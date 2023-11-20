
# Programming assignement 2
## Introduction
This code implements a small FPGA, consisting of 4-input and 6-input LUTs. The FPGA is able to map logic inputs onto the Look-Up Tables(LUTs) base on the available LUTs. The code also offers some helper functions to visualize and display the FPGA layout.

## Authors
Xiteng Yao
Shining Yang

## Repo structure

The main file is Virtual_FPGA.py. It has all the codes and features we implemented.

## Understanding the code

### Class LUT
<ol>
    <li>__init__: Initializes the LUT with a given number of inputs and a given SOP expression.
    <li>logic_to_truth_table: Converts a given SOP expression into a truth table.
</ol>

### Class VirFPGA
<ol>
    <li>__init__: Initializes the virtual FPGA with SOP expressions and the number of available LUTs.
    <li>map_sop_to_LUTs: Maps SOP expressions to LUT configurations and identifies input and output variables.
    <li>decompose_term: Breaks down a SOP term into subterms that fit into LUTs.
    <li>get_optimal_subterm: Determines the best subterm to fit into available LUTs based on term length and LUT availability.
    <li>combine_terms: Combines multiple terms into a single term using an intermediate variable for complex expressions.
    <li>create_combined_lut: Creates a final LUT for each output variable by combining related terms.
    <li>connect_LUT: Establishes connections between LUTs based on SOP logic.
    <li>output_bitstream: Outputs the current FPGA configuration as a JSON file.
    <li>readin_bitstream: Restores the FPGA configuration from a previously saved JSON file.
    <li>display_all_info: Prints detailed information about the FPGA configuration, including LUTs and connections.
    <li>display_LUT_usage: Displays usage statistics of 4-input and 6-input LUTs.
    <li>draw_diagram: Generates a visual diagram of the FPGA layout showing LUTs, inputs, and outputs.
</ol>

## Requirements
Python 3.x
Graphviz library for diagram rendering
Regular expressions (re) module
itertools module

## References
<ol>
    <li>https://graphviz.readthedocs.io/en/stable/examples.html</li>
    <li>https://stackoverflow.com/questions/11479624/is-there-a-way-to-guarantee-hierarchical-output-from-networkx</li>
    <li>https://towardsdatascience.com/graph-visualisation-basics-with-python-part-iii-directed-graphs-with-graphviz-50116fb0d670</li>
</ol>