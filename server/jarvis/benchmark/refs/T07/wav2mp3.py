import argparse, os, re, subprocess, sys
a = argparse.ArgumentParser(); a.add_argument('src'); a.add_argument('--out', required=True); a = a.parse_args()
if not os.path.isfile(a.src): sys.exit(2)
subprocess.run(['ffmpeg', '-hide_banner', '-nostdin', '-y', '-i', a.src, '-b:a', '128k', a.out], check=True, capture_output=True)
o = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=nw=1:nk=1', a.out], capture_output=True, text=True).stdout
print(f'Dauer: {float(o):.1f}')
