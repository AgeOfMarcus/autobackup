'''
fully working, no arg to restore files though
need to change cloud service for quicker up/down
'''
from filewatch import walk, hash as gethash	
import jsonstore, json_store_client, hashlib
import argparse, time, base64, json, os

SLASH = '/' if '/' in os.getcwd() else '\\'

class AutoBackup(object):
	def __init__(self, secret):
		self.storage = jsonstore.Client()
		self.fstorage = json_store_client.Client(
			(hashlib.sha256(secret.encode()).hexdigest()*64)[:64])

	def scan(self, d):
		f = walk(d)
		return {fn:h for fn,h in zip(
			f,[gethash(x) for x in f])}
	def get_changes(self, d):
		db = self.db_read()
		if not d in db:
			res = {fn:"created" for fn in self.scan(d).keys()}
			db[d] = res
			self.db_save(db)
			return res
		else:
			old = db[d]
			new = self.scan(d)
			res = {}
			for fn in old:
				if not fn in new:
					res[fn] = "deleted"
				elif not old[fn] == new[fn]:
					res[fn] = "changed"
			for fn in new:
				if not fn in old:
					res[fn] = "created"
			db[d] = res
			self.db_save(db)
			return res

	def db_read(self):
		res = self.fstorage.retrieve("db")
		return json.loads(base64.b64decode(res).decode()) if res else {}
	def db_save(self, db):
		self.fstorage.store("db", base64.b64encode(json.dumps(db).encode()).decode())

	def c_locations(self):
		res = self.fstorage.retrieve("files")
		return json.loads(base64.b64decode(res).decode()) if res else {}
	def c_upload(self, fn):
		fd = open(fn,"rb").read()
		loc = self.c_locations()
		loc[fn] = self.storage.store(fd)
		self.fstorage.store("files", base64.b64encode(json.dumps(loc).encode()).decode())
	def c_delete(self, fn):
		loc = self.c_locations()
		del loc[fn]
		self.fstorage.store("files", base64.b64encode(json.dumps(loc).encode()).decode())
	def c_download(self, fn):
		loc = self.c_locations()[fn]
		return self.storage.retrieve(*loc)

	def parse_changes(self, c):
		for fn, reason in c.items():
			if reason == "deleted":
				self.c_delete(fn)
			elif reason == "changed" or reason == "created":
				self.c_upload(fn)

	def run_once(self, d):
		self.parse_changes(self.get_changes(d))

	def restore(self, fn):
		fd = self.c_download(fn)
		d = os.path.dirname(fn)
		if not os.path.exists(d):
			os.makedirs(d)
		with open(fn, "wb") as f:
			f.write(fd)
	def restore_all(self):
		for fn in self.c_locations():
			self.restore(fn)


def parse_args():
	p = argparse.ArgumentParser()
	p.add_argument(
		"-s","--secret",
		help=("Secret key used to store data in the cloud"),
		required=True)
	p.add_argument(
		"-o","--once",
		help=("Run once"),
		action="store_true")
	p.add_argument(
		"-t","--time",
		help=("Run a scan every x seconds"),
		type=int)
	p.add_argument(
		"-d","--dir",
		help=("Directory to watch, default is current directory"))
	args = p.parse_args()
	if args.once and args.time:
		p.error("-o/--once and -t/--time cannot be used in conjunction")
	if not (args.once or args.time):
		p.error("nothing to do. -o/--once or -t/--time must be specified")
	return args

def main(args):
	ab = AutoBackup(args.secret)

	d = args.dir or os.getcwd()
	if d == '.':
		d = os.getcwd()
	elif d == '..':
		d = SLASH.join(os.getcwd().split(SLASH)[:-1])
	d = d.strip(SLASH)

	if args.once:
		ab.run_once(d)
	elif args.time:
		while True:
			ab.run_once(d)
			time.sleep(args.time)

main(parse_args()) if __name__ == "__main__" else None