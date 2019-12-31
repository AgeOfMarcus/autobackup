'''
everything works but it bugs out when a file is deleted
using a diryy fix 

add option to notice folders
'''

import os, argparse

SLASH = '/' if '/' in os.getcwd() else '\\'

def parse_args():
	p = argparse.ArgumentParser()
	p.add_argument(
		"DIR",
		help=("Directory to watch"))
	p.add_argument(
		"--hash",
		help=("Hash function to use, default sha256sum"))
	p.add_argument(
		"-s","--special",
		help=("Include files beginning with a '.', default=off"),
		action="store_true")
	return p.parse_args()

def walk(d: str, special=False):
	'''
	Gets a list of files in a directory recursively.

	:param d: str, directory name.
	:rtype: list
	'''
	w = [x for x in os.walk(d)]
	res = []
	for chunk in w:
		path = chunk[0]
		for file in chunk[-1]:
			fn = os.path.join(path, file)
			if True in [x.startswith(".") for x in fn.split(SLASH) if not (x == '.' or x == '..')]:
				if special:
					res.append(fn)
			else:
				res.append(fn)
	return res

def hash(fn: str, cmd="sha256sum"):
	'''
	Uses os.popen to get the hash value of a file

	:param fn: str, filename
	:param cmd: str, default="sha256sum", command used to get hash
	:rtype: str
	'''
	res = ''.join([x for x in os.popen("%s %s" % (cmd,fn))]).strip()
	h = res.split(" ")[0]
	return h

def watch(d: str, hashcmd="sha256sum", on_change=(lambda f,t: print(t,":",f)), special=False):
	'''
	Watch files for changes.

	:param d: str, base directory to watch
	:param hashcmd: str, hash function to use
	:param on_change: function, runs when change detected, must take filename and change type (str) as arguments
	'''
	files_ = walk(d, special=special)
	files = {f:h for f,h in zip(files_, [hash(x, cmd=hashcmd) for x in files_])}
	todel = []

	while True:
		# check for deleted files - doesn't seem to work
		new_w = walk(d, special=special)
		if not files_ == new_w:
			deleted = [i for i in files_ if not i in new_w]
			files_ = new_w
			for fn in deleted:
				del files[fn]
				on_change(fn, "deleted")

		# check for changes in files
		for fn in files:
			if not files[fn] == hash(fn, cmd=hashcmd):
				if hash(fn, cmd=hashcmd) == '':
					on_change(fn, "deleted")
					todel.append(fn)
					continue
				on_change(fn, "changed")
				files[fn] = hash(fn, cmd=hashcmd)
		# remove deleted files
		for fn in todel:
			del files[fn]
			todel.remove(fn)

		# check for new files
		new_w = walk(d, special=special)
		if not files_ == new_w:
			new = [i for i in new_w if not i in files_]
			files_ = new_w
			for f in new:
				on_change(f, "created")
				files[f] = hash(f, cmd=hashcmd)

def main(args):
	hf = args.hash or "sha256sum"
	watch(args.DIR, hashcmd=hf, special=(args.special or False))

main(parse_args()) if __name__ == "__main__" else None