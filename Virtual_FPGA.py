from itertools import count
import re
import itertools
import json

from graphviz import Digraph


def find_literals(expre):
    # Find output variable and all input variables
    output, input_list = expre.split('=')
    input_chars = []
    for char in input_list:
        if (char.isalpha() or char.islower()) and char not in input_chars:
            input_chars.append(char)
    input_chars.sort()

    return output, input_chars  # Find output variable and all input variables


def func_to_dic(expre):
    # Given a logic equation, generate its truth table
    val = [0, 1]
    truth_dic = {}

    simple_expre = expre.split('=')[1]

    literals = re.findall(r'[A-Za-z0-9]+', simple_expre)
    literals = list(set(literals))
    literals.sort()

    # print(literals)
    simple_expre = simple_expre.replace('*', ' and ').replace('+', ' or ')
    # print(simple_expre)
    for values in itertools.product(val, repeat=len(literals)):
        # print(values)
        context = dict(zip(literals, values))
        output = eval(simple_expre, {}, context)
        truth_dic[tuple(values)] = output

    return truth_dic  # Generate Truth table for LUTs


class LUT:
    def __init__(self, input_vars, output_var, function, dictionary):
        self.input = input_vars
        self.output = output_var
        self.bits = len(input_vars)
        self.func = function
        self.dic = dictionary

    def display_dic(self):
        for key, value in self.dic.items():
            print(f"{key}:{value}")


def connection_config(LUTs_list):
    # For a LUTs_list, generate connections
    connection_list = []
    for lut_a in LUTs_list:
        for lut_b in LUTs_list:
            for i in range(len(lut_b.input)):
                if lut_a.output == lut_b.input[i]:
                    # Create the connection word for each match
                    connection_word = [lut_a.func, 'output link to', lut_b.func, 'input', lut_b.input[i]]
                    # Convert the list to a string
                    connection_str = " ".join(connection_word)
                    # Check if the connection string is already in the list
                    if connection_str not in connection_list:
                        connection_list.append(connection_str)

    return connection_list


class VirFGPA:

    def __init__(self, sop_dict, total_4_input_LUTs=100, total_6_input_LUTs=100):
        self.sop_dict = sop_dict
        self.LUTs_list = []
        self.connection = []

        self.total_4_input_LUTs = total_4_input_LUTs
        self.total_6_input_LUTs = total_6_input_LUTs

        self.available_4_inputs_LUTs = total_4_input_LUTs
        self.available_6_inputs_LUTs = total_6_input_LUTs


    def map_sop_to_LUTs(self):
        intermediate_vars = count(1)

        for output_var, product_terms in self.sop_dict.items():
            all_combined_terms = []

            for term in product_terms:
                decomposed_terms = self.decompose_term(term, intermediate_vars)
                all_combined_terms.append(decomposed_terms)

            self.create_combined_lut(output_var, all_combined_terms, intermediate_vars)

    def decompose_term(self, term, intermediate_vars):
        decomposed_terms = []
        while term:
            sub_term, term = self.get_optimal_subterm(term)
            intermediate_var = f"Int{next(intermediate_vars)}"
            decomposed_terms.append(intermediate_var)

            truth_dic = func_to_dic(f"{intermediate_var} = {' & '.join(sub_term)}")
            LUT_inst = LUT(sub_term, intermediate_var, f"{intermediate_var} = {' & '.join(sub_term)}", truth_dic)
            self.LUTs_list.append(LUT_inst)

        return decomposed_terms

    def get_optimal_subterm(self, term):
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

    def create_combined_lut(self, output_var, all_combined_terms, intermediate_vars):
        # Combining all terms into a final LUT
        final_terms = []
        for terms in all_combined_terms:
            if len(terms) == 1:
                final_terms.append(terms[0])
            else:
                combined_term = self.combine_terms(terms, intermediate_vars)
                final_terms.append(combined_term)

        self.create_final_lut(output_var, final_terms)

    def combine_terms(self, terms, intermediate_vars):
        # Combining terms into a single LUT
        intermediate_var = f"Int{next(intermediate_vars)}"
        combined_expr = ' & '.join(terms)
        truth_dic = func_to_dic(f"{intermediate_var} = {combined_expr}")
        LUT_inst = LUT(terms, intermediate_var, f"{intermediate_var} = {combined_expr}", truth_dic)
        self.LUTs_list.append(LUT_inst)
        return intermediate_var

    def create_final_lut(self, output_var, final_terms):
        # Create the final LUT that ORs the outputs of the combined LUTs
        final_expr = ' | '.join(final_terms)
        if not any(lut.output == output_var for lut in self.LUTs_list):
            truth_dic = func_to_dic(f"{output_var} = {final_expr}")
            LUT_inst = LUT(final_terms, output_var, f"{output_var} = {final_expr}", truth_dic)
            self.LUTs_list.append(LUT_inst)
    def connect_LUT(self):
        self.connection = {}
        for i, lut_a in enumerate(self.LUTs_list):
            for j, lut_b in enumerate(self.LUTs_list):
                if i != j and lut_a.output in lut_b.input:
                    if i not in self.connection:
                        self.connection[i] = []
                    self.connection[i].append(j)
        return self.connection

    def output_bitstream(self):
        bitstream_data = {
            "LUTs": [{"id": i, "inputs": lut.input, "output": lut.output, "function": lut.func} for i, lut in
                     enumerate(self.LUTs_list)],
            "connections": self.connection
        }
        bitstream_json = json.dumps(bitstream_data, indent=4)
        # print(bitstream_json)
        with open('bitstream.json', 'w') as file:
            file.write(bitstream_json)
        return 0

    def readin_bitstream(self):
        with open('bitstream.json', 'r') as file:
            bitstream_data = json.load(file)
            self.LUTs_list = [LUT(lut["inputs"], lut["output"], lut["function"], func_to_dic(lut["function"])) for
                              lut in bitstream_data["LUTs"]]
            self.connection = bitstream_data["connections"]
        return self.LUTs_list, self.connection


    def display_all_info(self, truth_table_enable=0):
        # Display LUT information
        print("LUT Information:")
        for i, lut in enumerate(self.LUTs_list):
            print(f"LUT {i} (Output: {lut.output}):")
            print(f"  Inputs: {', '.join(lut.input)}")
            print(f"  Function: {lut.func}")
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
        dot = Digraph(comment='The FPGA Diagram')

        # Add nodes for LUTs
        for i, lut in enumerate(self.LUTs_list):
            dot.node(str(i), f'LUT {i}\n{lut.func}')

        # Add edges for connections
        for start, ends in self.connection.items():
            for end in ends:
                dot.edge(str(start), str(end))

        # Render the diagram to a file (e.g., in PDF format)
        dot.render('fpga_diagram', view=True)


# Example SOP Dictionary
sop_dict = {
    "X": [['a', 'c'], ['a', 'c', 'b'], ['b', 'd']],
    "Y": [['X', 'd']],
    "Z": [['X', 'a'], ['X', 'c', 'd']],
    "W": [['X', 'Y', 'Z'], ['X', 'Z', 'a'], ['X', 'Y']]
}
Vir_FPGA_instance = VirFGPA(sop_dict)
Vir_FPGA_instance.map_sop_to_LUTs()
Vir_FPGA_instance.connect_LUT()
Vir_FPGA_instance.output_bitstream()

Vir_FPGA_instance.readin_bitstream()
Vir_FPGA_instance.display_all_info()
Vir_FPGA_instance.display_LUT_usage()

# # Example SOP Dictionary


sop_dict = {
    "X": [['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p'],
          ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'q'],
          ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'r']],
    "Y": [['X', 't'], ['X', 'r']]
}

Vir_FPGA_instance = VirFGPA(sop_dict)
Vir_FPGA_instance.map_sop_to_LUTs()
Vir_FPGA_instance.connect_LUT()
Vir_FPGA_instance.output_bitstream()

Vir_FPGA_instance.readin_bitstream()
Vir_FPGA_instance.display_all_info()
Vir_FPGA_instance.display_LUT_usage()


Vir_FPGA_instance2 = VirFGPA({})
Vir_FPGA_instance2.readin_bitstream()
Vir_FPGA_instance2.draw_diagram()

'''
What to do next?
1. Inter-dependent SOP functions Done
2. Logic expression decomposition Done
3. Output bitstream file and restore from a bitstream file   Corrected tons of bugs
4. A resource allocation summary    Done
5. A visual representation    !!!Diagram
'''
