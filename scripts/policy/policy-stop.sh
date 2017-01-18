#! /bin/bash 
read PID < /home/ubuntu/pid_file
sudo kill -9 $PID


