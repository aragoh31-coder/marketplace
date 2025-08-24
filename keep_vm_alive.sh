#!/bin/bash

# Keep VM alive for 1 hour
echo "Starting VM keep-alive for 1 hour at $(date)"
echo "This will prevent the VM from timing out due to inactivity"

END_TIME=$(($(date +%s) + 3600))  # 1 hour from now

while [ $(date +%s) -lt $END_TIME ]; do
    REMAINING=$((($END_TIME - $(date +%s)) / 60))
    echo "[$(date)] VM Keep-alive ping - $REMAINING minutes remaining"
    
    # Do some light activity to keep the VM active
    ls /workspace > /dev/null 2>&1
    df -h > /dev/null 2>&1
    
    # Sleep for 1 minute
    sleep 60
done

echo "Keep-alive completed at $(date)"