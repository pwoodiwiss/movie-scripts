#!/usr/bin/python

import os
import os.path
import re
import sys
import StringIO
import subprocess

def filter_dict(theDictList, keys):
   return map(lambda a: { theKey: a[theKey] for theKey in keys if (theKey in a)}, theDictList)


# change this for other languages (3 character code)
LANG = "eng"

# set this to the path for mkvmerge
MKVMERGE = "/usr/bin/mkvmerge"

TRACK_LINE_RE = re.compile(r"Track ID (\d+): (\S+) \([^\)]+\) \[([^\]]*)\].*")

if len(sys.argv) < 2:
    print "Please supply an input directory"
    sys.exit()

in_dir = sys.argv[1]

for root, dirs, files in os.walk(in_dir):
    for f in files:

        # filter out non mkv files
        if not f.endswith(".mkv"):
            continue

        # path to file
        path = os.path.join(root, f)
        
        print "checking", path

        # build command line
        cmd = [MKVMERGE, "--identify-verbose", path]

        # get mkv info
        mkvmerge = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = mkvmerge.communicate()
        if mkvmerge.returncode != 0:
            print >> sys.stderr, "mkvmerge failed to identify", path
            continue

        # find audio and subtitle tracks
        audio = []
        subtitle = []
        video = []
        unknownTrack = []
        for line in StringIO.StringIO(stdout):
            lm = TRACK_LINE_RE.match(line)
            if lm:
              trackprops = dict(x.split(':') for x in lm.groups()[2].split(' '))
              trackprops['track-id'] =  lm.groups()[0]
              trackprops['track-type'] = lm.groups()[1]
              #print line
              if trackprops['track-type'] == 'audio':
                 audio.append(trackprops)
              elif trackprops['track-type'] == 'subtitles':
                 subtitle.append(trackprops)
              elif trackprops['track-type'] == 'video':
                 video.append(trackprops)
              else:
                 unknownTrack.append(line)
            #else:
            #  unknownTrack.append(line)
            
        if len(unknownTrack) != 0:
            print >> sys.stderr, "unknown tracks for", path
            print >> sys.stderr, unknownTrack
            continue
            
        # filter out files that don't need processing
        if len(audio) < 2 and len(subtitle) < 2:
            print >> sys.stderr, "nothing to do for", path
            continue

        # filter out tracks that don't match the language	
        audio_lang = filter(lambda a: a['language']==LANG, audio)
        subtitle_lang = filter(lambda a: a['language']==LANG, subtitle)

        # if no audio track found look undefied
        if len(audio_lang) == 0:
            audio_lang = filter(lambda a: a['language']=="und", audio)


        # filter out files that don't need processing
        if len(audio_lang) == 0:
            print >> sys.stderr, "no audio tracks with that language in", path
            continue

        # filter out files that don't need processing
        if len(audio_lang) == len(audio) and len(subtitle) == len(subtitle_lang):
            print >> sys.stderr, "no change in tracks or audio for", path
            continue

        # build command line
        cmd = [MKVMERGE, "-o", path + ".temp"]
        if len(audio_lang):
            cmd += ["--audio-tracks", ",".join([str(a['track-id']) for a in audio_lang])]
            for i in range(len(audio_lang)):
                cmd += ["--default-track", ":".join([audio_lang[i]['track-id'], "0" if i else "1"])]
        if len(subtitle_lang):
            cmd += ["--subtitle-tracks", ",".join([str(s['track-id']) for s in subtitle_lang])]
            for i in range(len(subtitle_lang)):
                cmd += ["--default-track", ":".join([subtitle_lang[i]['track-id'], "0"])]
        cmd += [path]

        # process file
        print >> sys.stderr, "Processing", path, "..."

        keyList = ['track-id','language', 'track_name', 'forced_track']
        print "Orig Audio: ", filter_dict(audio, keyList)
        print " New Audio: ", filter_dict(audio_lang, keyList)

        print " Orig Subs: ", filter_dict(subtitle, keyList)
        print "  New Subs: ", filter_dict(subtitle_lang, keyList)

        print cmd
        #mkvmerge = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        #stdout, stderr = mkvmerge.communicate()
        #if mkvmerge.returncode != 0:
        #    print >> sys.stderr, "Failed"
        #    continue
        
        #print >> sys.stderr, "Succeeded"

        # overwrite file
        # os.remove(path)
        # os.rename(path + ".temp", path)
