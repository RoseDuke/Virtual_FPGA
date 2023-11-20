from itertools import count
import re
import itertools
import json
from graphviz import Digraph

def find_literals(expre):
    output, input_list = expre.split('=')
    input_chars = set()
    for char in re.findall(r'[A-Za-z0-9]+', input_list):
        input_chars.add(char.rstrip("_'"))
    return output, sorted(input_chars)

class LUT:
    def __init__(self, input_vars, output_var, logic):
        self.input = input_vars
        self.output = output_var
        self.bits = len(input_vars)
        self.logic = logic
        self.truth_table = self.logic_to_truth_table(logic)

    def logic_to_truth_table(self, expre):
        """
        Converts a logic expression to a truth table.

        Args:
        expre (str): A logic expression in the format "output_var = input_expression".

        Returns:
        dict: A dictionary representing the truth table, mapping input value tuples to output values.
        """
        # Define possible binary values for truth table
        val = [0, 1]
        truth_dic = {}

        # Extract the right-hand side of the equation for evaluation
        simple_expre = expre.split('=')[1]

        # Collect unique literals while handling inverse notation (e.g., a')
        literals = set()
        for literal in re.findall(r'[A-Za-z0-9]+', simple_expre):
            literals.add(literal.rstrip("_'"))  # Remove any inverse notation
        literals = sorted(literals)

        # Replace logical operators for Python's eval function
        simple_expre = simple_expre.replace('*', ' and ').replace('+', ' or ')

        # Generate truth table by evaluating the expression for each combination of input values
        for values in itertools.product(val, repeat=len(literals)):
            context = dict(zip(literals, values))
            # Adjust context for inverses (e.g., a' or a_)
            for lit in literals:
                context[lit + "_"] = not context[lit]  # Inverse logic
                context[lit + "'"] = not context[lit]  # Alternative notation
            output = eval(simple_expre, {}, context)
            truth_dic[tuple(values)] = output

        return truth_dic


class VirFGPA:

    def __init__(self, sop_dict={}, total_4_input_LUTs=100, total_6_input_LUTs=100):
        self.sop_dict = sop_dict
        self.LUTs_list = []
        self.connection = []

        self.input_vars = set()
        self.output_vars = set()

        self.total_4_input_LUTs = total_4_input_LUTs
        self.total_6_input_LUTs = total_6_input_LUTs

        self.available_4_inputs_LUTs = total_4_input_LUTs
        self.available_6_inputs_LUTs = total_6_input_LUTs


    def map_sop_to_LUTs(self):
        """
        Maps the given SOP expressions to LUTs.
        Decomposes complex expressions into smaller sub-expressions and creates LUTs accordingly.
        """
        intermediate_vars = count(1)
        generated_vars = set()

        for output_var, product_terms in self.sop_dict.items():
            self.output_vars.add(output_var)
            all_combined_terms = []

            for term in product_terms:
                decomposed_terms = self.decompose_term(term, intermediate_vars)
                all_combined_terms.append(decomposed_terms)

            self.create_combined_lut(output_var, all_combined_terms, intermediate_vars)

            # Identifying input variables
            for term in product_terms:
                for var in term:
                    if var not in generated_vars:
                        self.input_vars.add(var)

            generated_vars.add(output_var)

        # Exclude generated intermediate variables from input variables
        self.input_vars -= generated_vars

    def decompose_term(self, term, intermediate_vars):
        """
        Decomposes a single SOP term into smaller subterms that fit into the available LUTs.
        """
        decomposed_terms = []
        while term:
            sub_term, term = self.get_optimal_subterm(term)
            intermediate_var = f"Int{next(intermediate_vars)}"
            decomposed_terms.append(intermediate_var)

            LUT_inst = LUT(sub_term, intermediate_var, f"{intermediate_var} = {' & '.join(sub_term)}")
            self.LUTs_list.append(LUT_inst)

        return decomposed_terms

    def get_optimal_subterm(self, term):
        """
        Chooses the optimal subterm to fit into a LUT based on available LUTs and term length.
        """
        if len(term) <= 4:
            if self.available_4_inputs_LUTs > 0:
                # Prioritize 4-input LUT for smaller terms
                sub_term = term
                self.available_4_inputs_LUTs -= 1
            elif self.available_6_inputs_LUTs > 0:
                # Use a 6-input LUT if no 4-input LUTs are available
                sub_term = term
                self.available_6_inputs_LUTs -= 1
            else:
                raise Exception("Not enough LUTs available")
        elif len(term) > 6 and self.available_6_inputs_LUTs > 0:
            # Use 6-input LUT for larger terms
            sub_term = term[:6]
            self.available_6_inputs_LUTs -= 1
        elif self.available_4_inputs_LUTs > 0:
            # If a term is larger than 4 but smaller than 7, and there are no 6-input LUTs, split it for 4-input LUTs
            sub_term = term[:4]
            self.available_4_inputs_LUTs -= 1
        else:
            raise Exception("Not enough LUTs available")

        return sub_term, term[len(sub_term):]

    def combine_terms(self, terms, intermediate_vars):
        """
        Combines multiple terms into a single term using an intermediate variable.
        """
        # Combining terms into a single LUT
        intermediate_var = f"Int{next(intermediate_vars)}"
        combined_expr = ' & '.join(terms)
        LUT_inst = LUT(terms, intermediate_var, f"{intermediate_var} = {combined_expr}")
        self.LUTs_list.append(LUT_inst)
        return intermediate_var

    def create_combined_lut(self, output_var, all_combined_terms, intermediate_vars):
        """
        Creates a final LUT for a given output variable by combining all related terms.
        """
        # Combining all terms into a final LUT
        final_terms = []
        for terms in all_combined_terms:

            print(terms)
            if len(terms) == 1:
                final_terms.append(terms[0])
            else:
                combined_term = self.combine_terms(terms, intermediate_vars)
                final_terms.append(combined_term)

        self.create_final_lut(output_var, final_terms)

    def create_final_lut(self, output_var, final_terms):
        """
        Creates the final LUT for an output variable that combines all its terms.
        """
        # Create the final LUT that ORs the outputs of the combined LUTs
        final_expr = ' | '.join(final_terms)
        if not any(lut.output == output_var for lut in self.LUTs_list):
            LUT_inst = LUT(final_terms, output_var, f"{output_var} = {final_expr}")
            self.LUTs_list.append(LUT_inst)
    def connect_LUT(self):
        """
        connect the LUTs according to the SOP dictionary
        """
        self.connection = {}
        for i, lut_a in enumerate(self.LUTs_list):
            for j, lut_b in enumerate(self.LUTs_list):
                if i != j and lut_a.output in lut_b.input:
                    if i not in self.connection:
                        self.connection[i] = []
                    self.connection[i].append(j)
        return self.connection

    def output_bitstream(self):
        """
        output the bitstream file, which can be used to restore the FPGA
        """
        bitstream_data = {
            "LUTs": [{"id": i, "inputs": lut.input, "output": lut.output, "function": lut.logic} for i, lut in
                     enumerate(self.LUTs_list)],
            "connections": self.connection
        }
        bitstream_json = json.dumps(bitstream_data, indent=4)
        # print(bitstream_json)
        with open('bitstream.json', 'w') as file:
            file.write(bitstream_json)
        return 0

    def readin_bitstream(self):
        """
        read in a bitstream file and restore the FPGA
        """
        with open('bitstream.json', 'r') as file:
            bitstream_data = json.load(file)
            self.LUTs_list = [LUT(lut["inputs"], lut["output"], lut["function"]) for
                              lut in bitstream_data["LUTs"]]
            self.connection = bitstream_data["connections"]
        return self.LUTs_list, self.connection


    def display_all_info(self, truth_table_enable=0):
        """
        print all the information of the FPGA
        """

        print("Input Variables:", ", ".join(sorted(self.input_vars)))
        print("Output Variables:", ", ".join(sorted(self.output_vars)))

        # Display LUT information
        print("LUT Information:")
        for i, lut in enumerate(self.LUTs_list):
            print(f"LUT {i} (Output: {lut.output}):")
            print(f"  Inputs: {', '.join(lut.input)}")
            print(f"  Function: {lut.logic}")
            if truth_table_enable == 1:
                print("  Truth Table:")
                for key, value in lut.dic.items():
                    print(f"    {key}: {value}")
            print()

        # Display connection information
        print("Connection Information:")
        for start, ends in self.connection.items():
            # Ensure 'start' is an integer
            start = int(start)  # Convert to int if it's not already
            connection_descriptions = []
            for end in ends:
                end_lut = self.LUTs_list[end]  # 'end' should already be an integer
                connection_descriptions.append(f"LUT {end} (Output: {end_lut.output})")
            connections_str = ', '.join(connection_descriptions)
            start_output = self.LUTs_list[start].output
            print(f"LUT {start} (Output: {start_output}) is connected to: {connections_str}")
        print()

    def display_LUT_usage(self):
        # Calculate the number of used LUTs
        used_4_input_LUTs = self.total_4_input_LUTs - self.available_4_inputs_LUTs
        used_6_input_LUTs = self.total_6_input_LUTs - self.available_6_inputs_LUTs

        # Calculate usage percentages, handling division by zero
        percent_4_input_usage = (
                    used_4_input_LUTs / self.total_4_input_LUTs * 100) if self.total_4_input_LUTs > 0 else 0
        percent_6_input_usage = (
                    used_6_input_LUTs / self.total_6_input_LUTs * 100) if self.total_6_input_LUTs > 0 else 0

        # Display usage information
        print(f"4-input LUTs Usage: {used_4_input_LUTs}/{self.total_4_input_LUTs} ({percent_4_input_usage:.2f}%)")
        print(f"6-input LUTs Usage: {used_6_input_LUTs}/{self.total_6_input_LUTs} ({percent_6_input_usage:.2f}%)")

    def draw_diagram(self):
        """
        Creates a visual representation of the FPGA layout with nodes for LUTs, input, and output variables.
        """
        dot = Digraph(comment='The FPGA Diagram')

        # Add nodes for input variables
        for var in self.input_vars:
            dot.node(var, var, shape='ellipse', color='lightblue')

        # Add nodes for LUTs
        for i, lut in enumerate(self.LUTs_list):
            dot.node(str(i), f'LUT {i}\n{lut.logic}', shape='rectangle')

        # Add nodes for output variables
        for var in self.output_vars:
            dot.node(var + "_out", var, shape='ellipse', color='lightgreen')

        # Add edges for connections
        for start, ends in self.connection.items():
            for end in ends:
                dot.edge(str(start), str(end))

        # Connect input variables to their LUTs
        for lut in self.LUTs_list:
            for input_var in lut.input:
                if input_var in self.input_vars:
                    dot.edge(input_var, str(self.LUTs_list.index(lut)))

        # Connect LUTs to output variables
        for lut in self.LUTs_list:
            if lut.output in self.output_vars:
                dot.edge(str(self.LUTs_list.index(lut)), lut.output + "_out")

        # Render the diagram to a file (e.g., in PDF format)
        dot.render('fpga_diagram', view=True)


# Example SOP Dictionary
sop_dict = {
    "X": [['a', 'a_'], ['a', 'c', 'b'], ['b', 'd']],
    "Y": [['X', 'd']],
    "Z": [['X', 'a'], ['X', 'c', 'd']],
    "W": [['X', 'Y', 'Z'], ['X', 'Z', 'a'], ['X', 'Y']]
}

Vir_FPGA_instance = VirFGPA(sop_dict, 100, 100)
Vir_FPGA_instance.map_sop_to_LUTs()
Vir_FPGA_instance.connect_LUT()
Vir_FPGA_instance.output_bitstream()

Vir_FPGA_instance.readin_bitstream()
Vir_FPGA_instance.display_all_info()
Vir_FPGA_instance.display_LUT_usage()
# Vir_FPGA_instance.draw_diagram()


# Example SOP Dictionary 2

sop_dict = {
    "X": [['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p'],
          ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'q'],
          ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'r']],
    "Y": [['X', 't'], ['X', 'r']]
}

Vir_FPGA_instance = VirFGPA(sop_dict, 100, 0)
Vir_FPGA_instance.map_sop_to_LUTs()
Vir_FPGA_instance.connect_LUT()
Vir_FPGA_instance.output_bitstream()

Vir_FPGA_instance.readin_bitstream()
Vir_FPGA_instance.display_all_info()
Vir_FPGA_instance.display_LUT_usage()
# Vir_FPGA_instance.draw_diagram()

Vir_FPGA_instance2 = VirFGPA()
Vir_FPGA_instance2.readin_bitstream()


sop_dict_expanded = {
    "A": [['a', 'b', 'c'], ['d', 'e', 'f', 'g'], ['h', 'i', 'j']],
    "B": [['k', 'l', 'm', 'n'], ['o', 'p', 'q', 'r', 's'], ['t', 'u', 'v']],
    "C": [['w', 'x', 'y', 'z'], ['a_', 'b_', 'c_', 'd_'], ['e_', 'f_', 'g_', 'h_']],
    "D": [['i_', 'j_', 'k_'], ['l_', 'm_', 'n_', 'o_'], ['p_', 'q_', 'r_', 's_']],
    "E": [['t_', 'u_', 'v_', 'w_'], ['x_', 'y_', 'z_'], ['aa', 'bb', 'cc', 'dd']],
    "F": [['ee', 'ff', 'gg', 'hh'], ['ii', 'jj', 'kk', 'll'], ['mm', 'nn', 'oo', 'pp']],
    "G": [['qq', 'rr', 'ss'], ['tt', 'uu', 'vv', 'ww'], ['xx', 'yy', 'zz']],
    "H": [['aaa', 'bbb', 'ccc'], ['ddd', 'eee', 'fff'], ['ggg', 'hhh', 'iii']],
    "I": [['jjj', 'kkk', 'lll', 'mmm'], ['nnn', 'ooo', 'ppp', 'qqq'], ['rrr', 'sss', 'ttt']],
    "J": [['uuu', 'vvv', 'www'], ['xxx', 'yyy', 'zzz'], ['aaaa', 'bbbb', 'cccc']]
}
Vir_FPGA_instance = VirFGPA(sop_dict_expanded, 100, 0)
Vir_FPGA_instance.map_sop_to_LUTs()
Vir_FPGA_instance.connect_LUT()
Vir_FPGA_instance.output_bitstream()

Vir_FPGA_instance.readin_bitstream()
Vir_FPGA_instance.display_all_info()
Vir_FPGA_instance.display_LUT_usage()
# Vir_FPGA_instance.draw_diagram()

sop_dict_interconnected = {
    "A": [['x', 'y', 'z'], ['a', 'b', 'c']],
    "B": [['A', 'd', 'e'], ['f', 'g', 'h']],
    "C": [['i', 'j', 'k', 'B'], ['l', 'm', 'n']],
    "D": [['o', 'p', 'q', 'r'], ['C', 's', 't']],
    "E": [['D', 'u', 'v'], ['w', 'x_', 'y_']],
    "F": [['z_', 'aa', 'bb'], ['E', 'cc', 'dd']],
    "G": [['ee', 'ff', 'gg', 'F'], ['hh', 'ii', 'jj']],
    "H": [['kk', 'll', 'mm', 'G'], ['nn', 'oo', 'pp']],
    "I": [['H', 'qq', 'rr'], ['ss', 'tt', 'uu']],
    "J": [['vv', 'ww', 'xx'], ['yy', 'zz', 'I']]
}

Vir_FPGA_instance = VirFGPA(sop_dict_interconnected, 100, 0)
Vir_FPGA_instance.map_sop_to_LUTs()
Vir_FPGA_instance.connect_LUT()
Vir_FPGA_instance.output_bitstream()

Vir_FPGA_instance.readin_bitstream()
Vir_FPGA_instance.display_all_info()
Vir_FPGA_instance.display_LUT_usage()
#Vir_FPGA_instance.draw_diagram()

sop_dict_cyclic = {
    "A": [['x', 'y', 'z'], ['B', 'c', 'd']],
    "B": [['A', 'e', 'f'], ['g', 'h', 'i']],
    "C": [['B', 'j', 'k'], ['l', 'm', 'n'], ['o', 'A', 'p']],
    "D": [['q', 'r', 's'], ['C', 't', 'u']],
    "E": [['D', 'v', 'w'], ['C', 'x_', 'y_']],
    "F": [['z_', 'aa', 'bb'], ['E', 'cc', 'dd']],
    "G": [['ee', 'ff', 'D'], ['hh', 'ii', 'E']],
    "H": [['F', 'G', 'kk'], ['ll', 'mm', 'nn']],
    "I": [['oo', 'pp', 'H'], ['qq', 'rr', 'C']],
    "J": [['ss', 'tt', 'I'], ['uu', 'vv', 'ww'], ['xx', 'yy', 'zz']]
}

Vir_FPGA_instance = VirFGPA(sop_dict_cyclic, 100, 0)
Vir_FPGA_instance.map_sop_to_LUTs()
Vir_FPGA_instance.connect_LUT()
Vir_FPGA_instance.output_bitstream()

Vir_FPGA_instance.readin_bitstream()
Vir_FPGA_instance.display_all_info()
Vir_FPGA_instance.display_LUT_usage()
# Vir_FPGA_instance.draw_diagram()


sop_dict_cyclic = {
    "A": [['x', 'B', 'z']],
    "B": [['A', 'C', 'f'], ['A', 'C', 'i']],
    "C": [['B', 'j', 'k'], ['A', 'B', 'n'], ['o', 'A', 'p']],
}

Vir_FPGA_instance = VirFGPA(sop_dict_cyclic, 100, 0)
Vir_FPGA_instance.map_sop_to_LUTs()
Vir_FPGA_instance.connect_LUT()
Vir_FPGA_instance.output_bitstream()

Vir_FPGA_instance.readin_bitstream()
Vir_FPGA_instance.display_all_info()
Vir_FPGA_instance.display_LUT_usage()
Vir_FPGA_instance.draw_diagram()


'''
To do list:
1. Inter-dependent SOP functions Done
2. Logic expression decomposition Done
3. Output bitstream file and restore from a bitstream file  Corrected tons of bugs
4. A resource allocation summary    Done
5. A visual representation    Done
'''
