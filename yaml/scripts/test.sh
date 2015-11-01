#!/bin/bash
func1(){ echo $TEST1; }
export -f func1
TEST1="shay"
export TEST1
sudo -E su root --shell /bin/bash -c "func1"

