
from itertools import count
import re
import itertools
import ast

def simplify_expre(expre_all): 
    #Transform the format like X=a*b+a*b*c+a*c+d+d*e+f into X=a*b+a*c+d+f; non-canonical to canonical
    expre = expre_all.split('=')[1]
    terms = expre.split('+')
    simplified_terms = []
    output_list =[]
    for term in terms:
        # For each term, check if it is covered by any other term
        is_redundant = False
        for other in terms:
            if term != other and all(char in term.split('*') for char in other.split('*')):
                is_redundant = True
                break
        if not is_redundant:
            simplified_terms.append(term)

    # Join the non-redundant terms to form the simplified expression
    output_list.append('+'.join(sorted(simplified_terms)))
    output_list.insert(0,'=')
    output_list.insert(0,expre_all.split('=')[0])
    return ''.join(output_list)

def find_literals(expre):
    #Find output variable and all input variables
    output, input_list = expre.split('=')
    input_chars = []
    for char in input_list:
        if (char.isalpha() or char.islower()) and char not in input_chars:
            input_chars.append(char)
    input_chars.sort()
    
    return output, input_chars #Find output variable and all input variables
    
def simple_logic(expre):
    #X=a*b+c*d to X=a and b or c and d
    output, input_list = expre.split('=')
    terms = input_list.split('+')  # Split the string at '+' to separate terms
    logical_terms = []

    for term in terms:
        # Insert ' and ' between each character in each term
        logical_term = ' and '.join(term)
        logical_terms.append(logical_term)

    # Join the terms with ' or '
    logical_expression = ' or '.join(logical_terms)
    
    return logical_expression
    
def func_to_dic(expre):
    #Given a logic equation, generate its truth table
    val = [0,1]
    truth_dic = {}
    
    simple_expre = expre.split('=')[1]
    
    literals = re.findall(r'[A-Za-z0-9]+', simple_expre)
    literals = list(set(literals))
    literals.sort()
    
    #print(literals)
    simple_expre = simple_expre.replace('*', ' and ').replace('+', ' or ')
    #print(simple_expre)
    for values in itertools.product(val, repeat=len(literals)):
        #print(values)
        context = dict(zip(literals, values))
        output = eval(simple_expre, {}, context)
        truth_dic[tuple(values)] = output

    return truth_dic #Generate Truth table for LUTs

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

def map_func_to_LUT_dependent(expression_list, num_of_bits):
    #Input logic expressions and number of bits, Return a LUTs_list
    num_of_expre = len(expression_list)
    LUTs_list = []
    for i in range(num_of_expre):
        truth_dic = func_to_dic(expression_list[i])
        LUT_inst = LUT(find_literals(expression_list[i])[1],find_literals(expression_list[i])[0],expression_list[i],truth_dic)
        LUTs_list.append(LUT_inst)
    
    #for i in range(num_of_expre):
        #print("the input bits of the {0:2d} LUT is {1:2d}".format(i, LUTs_list[i].bits))
        #print("which function does this LUT hold?" )
        #LUTs_list[i].display_dic()
        #print("\n")
    
    return LUTs_list

def connection_config(LUTs_list):
    #For a LUTs_list, generate connections
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
    def __init__(self, input_vars, output_var, input_val, function_list, bitstream_enable):
        self.input = input_vars
        self.output = output_var
        self.num_of_inputs = len(input_vars)
        self.input_val = input_val
        self.funclist = function_list
        self.read_from_bs = bitstream_enable
        self.LUTs_list = []
        self.connection = []
        self.truth_dic = {}
    
    def map_func_to_LUTs(self):
        #Generate LUTs_list
        self.LUTs_list = map_func_to_LUT_dependent(self.funclist, self.num_of_inputs)
        return self.LUTs_list
    
    def connect_LUT(self):
        #Generate connection Information
        #print(self.LUTs_list)
        self.connection = connection_config(self.LUTs_list)
        return self.connection
        
    def calcu_truthtable(self):
        #Calculate output based on input, all intermediate results are included
        finish = 0
        calculated_val = dict(zip(self.input, self.input_val))
        #print(calculated_val)
        while finish == 0:
            finish = 1
            for term in self.funclist:
                out_side, in_side = term.split('=')
                input_for_term = re.findall(r'[A-Za-z0-9]+', in_side)
                logic_expre = in_side.replace('*', ' and ').replace('+', ' or ')
                if all(char in calculated_val for char in input_for_term):
                    #All input variables is already in the calculated_val dictionary
                    #We can now get the output value for it
                    calculated_val[out_side] = eval(logic_expre,{},calculated_val)
                else:
                    #At least one of the expressions can't get all its input
                    finish = 0

        return calculated_val
    
    def output_bitstream(self):
        bit_stream = []
        #print(self.LUTs_list)
        for i in range(len(self.LUTs_list)):
            single_LUT_var = []
            single_LUT_var.append(i) #LUT id
            single_LUT_var.append(self.LUTs_list[i].bits) #LUT input len
            single_LUT_var.append(self.LUTs_list[i].func) #LUT function
            bit_stream.append(single_LUT_var)
        bit_stream.append(self.connection) #the last item is connection list
        print(bit_stream)
        with open('bitstream.txt', 'w') as file:
            file.write(str(bit_stream))
         
        return 0
            
    def readin_bitstream(self):
        if(self.read_from_bs == 1):
            LUT_readin_list = []
            with open('./bitstream.txt', 'r') as file:
                data = file.read()
                profile = ast.literal_eval(data)
                for lut_data in profile[:-1]:
                    lut_id, input_num, function = lut_data
                    #print(function)
                    output_var, input_vars = find_literals(function.replace('*', ''))
                    LUT_readin_list.append(LUT(input_vars, output_var, function, func_to_dic(function)))
            self.LUTs_list = LUT_readin_list
            self.connection = profile[-1]
            
            return self.LUTs_list, self.connection
            #do read in bitstream and generate diagram
            #bit stream format: 
        else:
            print('Not reading from bitstream')
    
    def draw_diagram(self):
        #Generate the schematic diagram here
        pass
    
expression1 = ['X=a*c+a*c*b+b*d','Y=X*d', 'Z=X*a+X*c*d','W=X*Y*Z+X*Z*a+X*Y'] #ab+ac+abc+d
Vir_FPGA_instance = VirFGPA(['a','b','c','d'], 'W', [0,1,0,1],expression1, 1)
Vir_FPGA_instance.map_func_to_LUTs()
Vir_FPGA_instance.connect_LUT()
#Vir_FPGA_instance.output_bitstream()
LUTs_list, connection = Vir_FPGA_instance.readin_bitstream()
for i in range(len(LUTs_list)):
    print(LUTs_list[i].input)
    print(LUTs_list[i].output)
    print(LUTs_list[i].bits)
    print(LUTs_list[i].func)
    print(LUTs_list[i].dic)

print(connection)
#print(calculated_valuelist)
#for i in range(len(expression1)):
#    expression1[i] = simplify_expre(expression1[i])
#print(expression1)
#print(find_literals(expression1[0])[0])
#print(find_literals(expression1[0])[1])
#print(func_to_dic(expression1[0]))
#print(connection_config(map_func_to_LUT_dependent(expression1,4)))

#LUTs_list = map_func_to_LUT_dependent(expression1,4)
#print(connection_config(LUTs_list))

'''
What to do next?
inter-dependent SOP functions DONE!
non-canonical expression to canonical expression *IMPORTANT! DONE!
logic expression decomposition, for example 7bits and gate -> 2 6bits and gate do and    !!!Decomposition
output bitstream file and restore from a bitstream file    !!!Bitstream
resource allocation summary    !!!Allocation
A visual representation    !!!Diagram
'''