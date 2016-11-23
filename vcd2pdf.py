#!/usr/bin/env python3

import sys;
import re;
from collections import namedtuple;

from pyx import *;

# CG1 - Date
# CG2 - Version
# CG3 - Timescale
# CG4 - Variable definitions
# CG5 - Initial values
# CG6 - Simulation data
FORMAT_REGEX = ("^\s*\$date\s*(.+?)\s*\$end"
                 "\s+\$version\s*(.+?)\s*\$end"
                 "\s+\$timescale\s*(.+?)\s*\$end"
                 "\s+(.*)\$enddefinitions"
                 "\s+\$end\s+(?:#0\s+)?\$dumpvars\s+(.*)\s+\$end"
                 "\s+(.*)\s*$");

# CG1 - scope or upscope
# CG2 - scope type
# CG3 - scope name
# CG4 - scope contents
SCOPE_REGEX = "\$((?:up)?scope)(?:\s+\$end|\s+(module)\s+(\w+)\s+\$end\s+((?:.(?!\$(?:up)?scope))*))";

# CG1 - variable type
# CG2 - Number of bits
# CG3 - ASCII shorthand
# CG4 - variable name
VAR_REGEX = "\$var\s+(wire|reg)\s+(\d)\s+(.)\s+(\w+)\s+\$end";

# CG1 - Time index
# CG2 - Variables that changed
TIME_REGEX = "#(\d+)\s*((?:[\db]+\s*[!-~]\s*)*)";

# CG1 - New value
# CG2 - Varaible
VALUE_REGEX = "(\w+)\s*([!-~])";


with open(sys.argv[1], 'r') as myfile:
    data=myfile.read();

result = re.match(FORMAT_REGEX, data, re.DOTALL);

if not result:
    print("Not a valid VCD file");
    sys.exit(1);

# Grab metadata
date = result.group(1);
version = result.group(2);
timescale = result.group(3);


# Grab all of the scopes
scopes = re.findall(SCOPE_REGEX, result.group(4), re.DOTALL);

# Grab all of the variables
Variable = namedtuple("Variable", ["scope", "name", "ascii", "changes"]);

variables = {};
activeScope = [];
for scope in scopes:
    if scope[0] == "scope":
        activeScope.append(scope[2]);
        variableText = re.findall(VAR_REGEX, scope[3]);
        for var in variableText:
            variables[var[2]] = Variable(activeScope[-1], var[3], var[2], []);

    elif scope[0] == "upscope":
        activeScope.pop();


# Grab the initial values
init = result.group(5);
values = re.findall(VALUE_REGEX, init);

for value in values:
    variables[value[1]].changes.append((0, value[0]));


# Grab all of the changes
last = 0
steps = re.findall(TIME_REGEX, result.group(6), re.DOTALL);
for step in steps:
    last = max(last, int(step[0]));
    deltas = re.findall(VALUE_REGEX, step[1]);
    for delta in deltas:
        variables[delta[1]].changes.append((int(step[0]), delta[0]));


# Add an end state to all of the variables
for key, var in variables.items():
    var.changes.append((last, ''));


# Draw the waveforms
c = canvas.canvas();

i = 0;
high = 0.422;
xscale = 0.15;

for key, var in variables.items():
    y = i;
    c.text(-0.2, y + (0.422 / 2.0), var.name.replace("_","\_"), [text.halign.boxright, text.valign.middle]);
    waveform = path.path(path.moveto(0, y + int(var.changes[0][1]) * high));
    for j in range(1, len(var.changes) - 1):
        waveform.append(path.lineto(xscale * var.changes[j][0], y + int(var.changes[j-1][1]) * high));
        waveform.append(path.lineto(xscale * var.changes[j][0], y + int(var.changes[j][1]) * high));
    waveform.append(path.lineto(xscale * var.changes[-1][0], y + int(var.changes[-2][1]) * high));
    c.stroke(waveform, []);
    i += 1;

# Fill and trim the canvas
bounds = c.bbox().enlarged(0.5);
bg = canvas.canvas([canvas.clip( bounds.path() )])
bg.fill(bounds.enlarged(1.0).path(), [color.rgb.white])

bg.insert(c);

# Write out
bg.writeEPSfile("out");
bg.writePDFfile("out");
bg.writeSVGfile("out");

