#!/bin/bash

# set environment variables
terminal_app=${ps -p $(ps -p $$ -o ppid=) -o comm=}

