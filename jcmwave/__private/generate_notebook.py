import argparse
import os
import shutil
import sys
import jinja2
from subprocess import call
import json

parser = argparse.ArgumentParser(description='Generate a Jupyter notebook.')
parser.add_argument('language', choices={"Matlab","JupyterNotebook"},
            help='Language of script to be generated.')
parser.add_argument('type', choices={"Optimization","ParameterScan","Driver"},
            help='Type of task to be generated.')
parser.add_argument('path',
            help='Path to script that is to be generated. E.g. /local/.../DataAnalysis')
parser.add_argument('project', 
            help='Name of jcm poject file. E.g. mie2D.jcmpt')
parser.add_argument('json_file',
            help='Path to file with JSON data on missing keys. E.g. {"MissingKeys":[{"name":"width"}]}')
args = parser.parse_args()

templateLoader = jinja2.FileSystemLoader(searchpath=os.path.dirname(os.path.abspath(__file__)))
templateEnv = jinja2.Environment(loader=templateLoader)

if args.language == "JupyterNotebook":
  fileEnding = "ipynb"
  if args.type == "ParameterScan":
      template = templateEnv.get_template("ParameterScanTemplate.ipynb")
  elif args.type == "Optimization":
      template = templateEnv.get_template("OptimizationTemplate.ipynb")
  elif args.type == "Driver":
      template = templateEnv.get_template("DriverTemplate.ipynb")
elif args.language == "Matlab":
  fileEnding = "m"
  if args.type == "ParameterScan":
      template = templateEnv.get_template("ParameterScanTemplate.m")
  elif args.type == "Optimization":
      template = templateEnv.get_template("OptimizationTemplate.m")
  elif args.type == "Driver":
      template = templateEnv.get_template("DriverTemplate.m")
        
with open(args.json_file,"r") as f: json_data = json.load(f)
    
params = json_data['MissingKeys']
style = {
    'user_input': 'color:#a00; font-weight:bold;',
    'optional': 'color:gray'
}
if args.type == "Driver":
    style['user_input'] = ''
    style['optional'] = ''

outputText = template.render(
    params=params,
    project=args.project,
    style=style
)

print(args.path+'.'+fileEnding)
print(outputText)
with open(args.path+'.'+fileEnding,'w') as f:
    f.write(outputText)
