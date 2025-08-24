#!/bin/bash

# Keep VM alive for 6 hours
echo "Starting VM keep-alive for 6 hours at $(date)"
echo "This will prevent the VM from timing out due to inactivity"

END_TIME=$(($(date +%s) + 21600))  # 6 hours from now (6 * 60 * 60 = 21600 seconds)

while [ $(date +%s) -lt $END_TIME ]; do
    CURRENT_TIME=$(date +%s)
    REMAINING_SECONDS=$(($END_TIME - $CURRENT_TIME))
    REMAINING_HOURS=$(($REMAINING_SECONDS / 3600))
    REMAINING_MINUTES=$((($REMAINING_SECONDS % 3600) / 60))
    
    echo "[$(date)] VM Keep-alive ping - ${REMAINING_HOURS}h ${REMAINING_MINUTES}m remaining"
    
    # Do some light activity to keep the VM active
    ls /workspace > /dev/null 2>&1
    df -h > /dev/null 2>&1
    ps aux > /dev/null 2>&1
    
    # Sleep for 5 minutes (300 seconds)
    sleep 300
done

echo "Keep-alive completed at $(date)"