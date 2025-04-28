#!/usr/bin/env python3
"""
Analyze RTL disassembly files to generate analysis outputs.
Usage: analyze_rtl.py --rtl <rtl_file> --function <function_name> --output-dir <output_dir>
"""
import sys
import re
import os
import argparse
import xml.etree.ElementTree as ET
from xml.dom import minidom

def extract_basic_blocks(rtl_file, function_name):
    """Extract basic blocks from RTL file for the specified function."""
    basic_blocks = {}
    current_bb = None
    bb_length = 0
    in_function = False
    
    with open(rtl_file, 'r') as f:
        for line in f:
            # Check if we're in the target function
            if f"{function_name}:" in line and not in_function:
                in_function = True
            elif "<" in line and ">" in line and in_function:
                # Exit if we reach another function
                if not line.strip().startswith(function_name):
                    break
                    
            if in_function:
                if line.strip().startswith("BB:"):
                    if current_bb is not None:
                        basic_blocks[current_bb] = bb_length
                    current_bb = line.strip().split(' ')[1]
                    bb_length = 0
                elif line.strip() and current_bb is not None and not line.strip().startswith("--"):
                    bb_length += 1
    
    # Add the last block
    if current_bb is not None:
        basic_blocks[current_bb] = bb_length
    
    return basic_blocks

def extract_edges(rtl_file, function_name):
    """Extract control flow edges from RTL file for the specified function."""
    edges = []
    current_bb = None
    in_function = False
    
    with open(rtl_file, 'r') as f:
        for line in f:
            # Check if we're in the target function
            if f"{function_name}:" in line and not in_function:
                in_function = True
            elif "<" in line and ">" in line and in_function:
                # Exit if we reach another function
                if not line.strip().startswith(function_name):
                    break
                    
            if in_function:
                if line.strip().startswith("BB:"):
                    current_bb = line.strip().split(' ')[1]
                elif ("goto" in line or "jump" in line or "branch" in line) and current_bb is not None:
                    # Extract target BB from jump instructions
                    match = re.search(r'-> (\w+)', line)
                    if match:
                        target_bb = match.group(1)
                        edges.append((current_bb, target_bb))
                elif "return" in line and current_bb is not None:
                    # Add edge to exit block for returns
                    edges.append((current_bb, '-1'))
    
    # Add fall-through edges
    all_bbs = set([e[0] for e in edges] + [e[1] for e in edges if e[1] != '-1'])
    
    for bb in all_bbs:
        outgoing = [e for e in edges if e[0] == bb]
        if not outgoing and bb != '-1':
            # Find the next block (assuming sequential numbering)
            try:
                next_bb = str(int(bb) + 1)
                if next_bb in all_bbs:
                    edges.append((bb, next_bb))
            except ValueError:
                pass
    
    return edges

def generate_edges_file(edges, output_file):
    """Generate Edges.txt file."""
    bb_edges = {}
    for src, dst in edges:
        if src not in bb_edges:
            bb_edges[src] = []
        bb_edges[src].append(dst)
    
    with open(output_file, 'w') as f:
        for bb in sorted(bb_edges.keys(), key=lambda x: int(x) if x != '-1' else float('inf')):
            f.write(f"BB: {bb}\n")
            for dst in bb_edges[bb]:
                f.write(f"\t{bb} --> {dst}\n")
            f.write("\n")

def generate_analysis_file(edges, basic_blocks, output_file):
    """Generate Analysis.txt file."""
    cond_edges = sum(1 for src in set(e[0] for e in edges) if sum(1 for e in edges if e[0] == src) > 1)
    uncond_edges = len(edges) - cond_edges
    
    with open(output_file, 'w') as f:
        f.write("Edge Analysis:\n")
        f.write(f"\tTotal amount of edges: {len(edges)}\n")
        f.write(f"\tNumber of unconditional edges: {uncond_edges}\n")
        f.write(f"\tNumber of conditional edges: {cond_edges}\n")
        f.write("------------------------------------------------------\n")
        f.write("Block Analysis:\n")
        f.write(f"\tTotal amount of basic blocks: {len(basic_blocks)}\n")
        
        for bb, length in sorted(basic_blocks.items(), key=lambda x: int(x[0]) if x[0] != '-1' else float('inf')):
            if bb != '-2':  # Skip the artificial entry block
                f.write(f"\tLength of basic block {bb}: {length}\n")

def generate_cfg_xml(edges, basic_blocks, output_file):
    """Generate CFG.xml file."""
    root = ET.Element("cfg")
    
    # Add nodes
    nodes = ET.SubElement(root, "nodes")
    for bb in basic_blocks:
        if bb != '-2':  # Skip the artificial entry block
            node = ET.SubElement(nodes, "node")
            node.set("id", bb)
            node.set("size", str(basic_blocks[bb]))
    
    # Add edges
    edges_elem = ET.SubElement(root, "edges")
    for src, dst in edges:
        edge = ET.SubElement(edges_elem, "edge")
        edge.set("source", src)
        edge.set("target", dst)
    
    # Write to file with pretty formatting
    xmlstr = minidom.parseString(ET.tostring(root)).toprettyxml(indent="    ")
    with open(output_file, 'w') as f:
        f.write(xmlstr)

def main():
    parser = argparse.ArgumentParser(description='Analyze RTL disassembly files')
    parser.add_argument('--rtl', required=True, help='Path to RTL disassembly file')
    parser.add_argument('--function', required=True, help='Function name to analyze')
    parser.add_argument('--output-dir', required=True, help='Output directory')
    
    args = parser.parse_args()
    
    # Extract basic blocks and edges
    basic_blocks = extract_basic_blocks(args.rtl, args.function)
    edges = extract_edges(args.rtl, args.function)
    
    # Generate output files
    generate_edges_file(edges, os.path.join(args.output_dir, "Edges.txt"))
    generate_analysis_file(edges, basic_blocks, os.path.join(args.output_dir, "Analysis.txt"))
    generate_cfg_xml(edges, basic_blocks, os.path.join(args.output_dir, "CFG.xml"))
    
    print(f"Analysis completed for {args.function} in {args.rtl}")
    print(f"Output files saved to {args.output_dir}")
    
if __name__ == "__main__":
    main() 