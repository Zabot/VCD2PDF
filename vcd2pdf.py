#!/usr/bin/env python3

import sys;
import re;
from collections import namedtuple;
from collections import defaultdict;

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
# CG5 - bus bits
VAR_REGEX = "\$var\s+(wire|reg)\s+(\d)\s+(.)\s+(\w+)\s+(?:\[(\d+:\d+)\]\s+)?\$end";

# CG1 - Time index
# CG2 - Variables that changed
TIME_REGEX = "#(\d+)\s*((?:[\db]+\s*[!-~]\s*)*)";

# CG1 - New value
# CG2 - Varaible
STATE_REGEX = "([\dxX]|[bB][0-9xX]+\s+)([!-~])";

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
Variable = namedtuple("Variable", ["scope", "name", "ascii", "bits", "states"]);

variables = defaultdict(list);
activeScope = [];
for scope in scopes:
    if scope[0] == "scope":
        activeScope.append(scope[2]);
        variableText = re.findall(VAR_REGEX, scope[3]);
        for var in variableText:
            variables[var[2]].append(Variable(activeScope[-1], var[3], var[2], int(var[1]), []));

    elif scope[0] == "upscope":
        activeScope.pop();

def parseState(startTime, stateMatch):
    if stateMatch[0].lower().startswith('b'):
        valueString = stateMatch[0][1:];

        # Value is a valid binary number
        try:
            value = int(stateMatch[0][1:], 2);

        # Value is not binary number, bits are floating or error
        except:
            value = valueString;

    else:
        try:
            value = int(stateMatch[0]);

        except:
            value = stateMatch[0];

    return State(startTime, value);


# Grab the initial states
State = namedtuple("State", ["startTime", "value"]);

initialStates = re.findall(STATE_REGEX, result.group(5));

for stateMatch in initialStates:
    for var in variables[stateMatch[1]]:
        var.states.append( parseState(0, stateMatch) );
    

# Grab all of the states
last = 0
steps = re.findall(TIME_REGEX, result.group(6), re.DOTALL);
for step in steps:
    last = max(last, int(step[0]));
    states = re.findall(STATE_REGEX, step[1]);
    for stateMatch in states:
        for var in variables[stateMatch[1]]:
            var.states.append( parseState(int(step[0]), stateMatch) );


# Add an end state to all of the variables
for key, varList in variables.items():
    for var in varList:
        var.states.append( State(last, '') );

# Draw the waveforms
c = canvas.canvas();


def drawWavePath(variable, canvas, x, y, xscale, yscale):
    states = variable.states;

    for j in range(0, len(var.states) - 1):
        if variable.bits == 1:
            if states[j].value == 'x':
                canvas.stroke(path.rect(x + states[j].startTime * xscale, y, x + (states[j + 1].startTime - states[j].startTime) * xscale, yscale), [color.rgb.black, deco.filled([color.cmyk.Gray])]);

            else:
                canvas.stroke(path.line(x + states[j].startTime * xscale, y + states[j].value * yscale, x + states[j+1].startTime * xscale, y + states[j].value * yscale));
                if states[j + 1].value != '':
                    canvas.stroke(path.line(x + states[j + 1].startTime * xscale, y + states[j].value * yscale, x + states[j + 1].startTime * xscale, y + states[j + 1].value * yscale));
        else:
            pass;
            # Draw bus


y = 0;
yscale = 0.422;
xscale = 0.15;
for key, varList in variables.items():
    for var in varList:
        c.text(-0.2, y + (0.422 / 2.0), var.scope + "::" + var.name.replace("_","\_"), [text.halign.boxright, text.valign.middle]);
        drawWavePath(var, c, 0, y, xscale, yscale);
        y += 1;

# Fill and trim the canvas
bounds = c.bbox().enlarged(0.5);
bg = canvas.canvas([canvas.clip( bounds.path() )])
bg.fill(bounds.enlarged(1.0).path(), [color.rgb.white])

bg.insert(c);

# Write out
bg.writeEPSfile("out");
bg.writePDFfile("out");
bg.writeSVGfile("out");

