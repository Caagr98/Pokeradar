#!/usr/bin/env python3

POKEMON_NAMES = [ "MissingNo", "Bulbasaur", "Ivysaur", "Venusaur", "Charmander",
		"Charmeleon", "Charizard", "Squirtle", "Wartortle", "Blastoise",
		"Caterpie", "Metapod", "Butterfree", "Weedle", "Kakuna", "Beedrill",
		"Pidgey", "Pidgeotto", "Pidgeot", "Rattata", "Raticate", "Spearow",
		"Fearow", "Ekans", "Arbok", "Pikachu", "Raichu", "Sandshrew",
		"Sandslash", "Nidoran ♀", "Nidorina", "Nidoqueen", "Nidoran ♂",
		"Nidorino", "Nidoking", "Clefairy", "Clefable", "Vulpix", "Ninetales",
		"Jigglypuff", "Wigglytuff", "Zubat", "Golbat", "Oddish", "Gloom",
		"Vileplume", "Paras", "Parasect", "Venonat", "Venomoth", "Diglett",
		"Dugtrio", "Meowth", "Persian", "Psyduck", "Golduck", "Mankey",
		"Primeape", "Growlithe", "Arcanine", "Poliwag", "Poliwhirl",
		"Poliwrath", "Abra", "Kadabra", "Alakazam", "Machop", "Machoke",
		"Machamp", "Bellsprout", "Weepinbell", "Victreebel", "Tentacool",
		"Tentacruel", "Geodude", "Graveler", "Golem", "Ponyta", "Rapidash",
		"Slowpoke", "Slowbro", "Magnemite", "Magneton", "Farfetchd", "Doduo",
		"Dodrio", "Seel", "Dewgong", "Grimer", "Muk", "Shellder", "Cloyster",
		"Gastly", "Haunter", "Gengar", "Onix", "Drowzee", "Hypno", "Krabby",
		"Kingler", "Voltorb", "Electrode", "Exeggcute", "Exeggutor", "Cubone",
		"Marowak", "Hitmonlee", "Hitmonchan", "Lickitung", "Koffing",
		"Weezing", "Rhyhorn", "Rhydon", "Chansey", "Tangela", "Kangaskhan",
		"Horsea", "Seadra", "Goldeen", "Seaking", "Staryu", "Starmie",
		"Mr_mime", "Scyther", "Jynx", "Electabuzz", "Magmar", "Pinsir",
		"Tauros", "Magikarp", "Gyarados", "Lapras", "Ditto", "Eevee",
		"Vaporeon", "Jolteon", "Flareon", "Porygon", "Omanyte", "Omastar",
		"Kabuto", "Kabutops", "Aerodactyl", "Snorlax", "Articuno", "Zapdos",
		"Moltres", "Dratini", "Dragonair", "Dragonite", "Mewtwo", "Mew" ]

import pgoapi
import pgoapi.utilities as pgoutil

import threading
import itertools
import os.path
import time
import sys
import platform

import argparse
import shlex
parser = argparse.ArgumentParser(fromfile_prefix_chars="@")
parser.convert_arg_line_to_args = shlex.split
parser.add_argument("provider", choices=["ptc", "google"])
parser.add_argument("username")
parser.add_argument("password")
parser.add_argument("-p", "--position", nargs=3, action="append", metavar=("NAME", "LAT", "LNG"), help="a position to scan")
parser.add_argument("-v", "--verbose", action="store_true", help="spam a lot of debug info")
parser.add_argument("-n", "--nidoran", action="store_true", help="replace Nidoran's suffixes with [MF], to help non-Unicode-aware terminals")
parser.add_argument("-c", "--coords",  action="store_true", help="print coords for found Pokemon")
args = parser.parse_args()

login = (args.provider, args.username, args.password)
locations = []
for name, lat, lng in args.position:
	locations.append((name, float(lat), float(lng)))
if args.verbose:
	import logging
	logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(module)10s] [%(levelname)5s] %(message)s')
	logging.getLogger("requests").setLevel(logging.WARNING)
	logging.getLogger("pgoapi").setLevel(logging.INFO)
	logging.getLogger("rpc_api").setLevel(logging.INFO)
if args.nidoran: #TODO I don't really want to have this. Make dad set his locale correctly.
	POKEMON_NAMES[29] = "Nidoran F"
	POKEMON_NAMES[32] = "Nidoran M"
print_coords = args.coords

def get_encrypt_lib():
	lib_name = ""
	if sys.platform == "win32":
		if platform.architecture()[0] == '64bit':
			lib_name = "encrypt64bit.dll"
		else:
			lib_name = "encrypt32bit.dll"
	elif sys.platform == "darwin":
		lib_name = "libencrypt-osx-64.so"
	elif os.uname()[4].startswith("arm") and platform.architecture()[0] == '32bit':
		lib_name = "libencrypt-linux-arm-32.so"
	elif sys.platform.startswith('linux'):
		if platform.architecture()[0] == '64bit':
			lib_name = "libencrypt-linux-x86-64.so"
		else:
			lib_name = "libencrypt-linux-x86-32.so"
	elif sys.platform.startswith('freebsd-10'):
		lib_name = "libencrypt-freebsd10-64.so"
	else:
		raise Exception("Unexpected/unsupported platform '{}'".format(sys.platform))

	if not os.path.isfile(lib_name):
		raise Exception("Could not find {} encryption library {}".format(sys.platform, lib_name))
	return os.path.join(os.path.dirname(os.path.realpath(__file__)), lib_name)

class PoGoScanner(threading.Thread):
	def __init__(self, login, locations):
		threading.Thread.__init__(self, daemon=True)
		self.login = login
		self.locations = locations
		self.event = threading.Event()
		self.delay = 10

	def run(self):
		self.running = True
		print("Logging in")
		api = pgoapi.PGoApi(provider=login[0], username=login[1], password=login[2])
		api.activate_signature(get_encrypt_lib())
		api.set_position(0, 0, 0) #Obviously wrong if anyone's looking, but so is all of this script
		status = api.get_player()
		print("Logged in")

		S_FIRSTLOOP = 1
		self.seen = {}
		locs = itertools.chain(self.locations, [S_FIRSTLOOP], itertools.cycle(self.locations))
		while self.running:
			self.event.wait()
			self.event.clear()
			loc = next(locs)
			if loc == S_FIRSTLOOP:
				self.delay = 20
				continue
			self.scan(api, *loc)
		print("Stopping (Unknown reason)")

	def get_pokemon(self, api, lat, lng):
		api.set_position(lat, lng, 40)
		cells = pgoutil.get_cell_ids(lat, lng, 70)
		response = api.get_map_objects(since_timestamp_ms=[0] * len(cells), cell_id=cells)
		r = response["responses"]["GET_MAP_OBJECTS"]
		pokemon = list(itertools.chain.from_iterable(cell.get("catchable_pokemons", []) for cell in r["map_cells"]))
		now = r["map_cells"][0]["current_timestamp_ms"]
		return pokemon, now
	
	def update(self, pokemon, now):
		for p in pokemon:
			self.seen[p["encounter_id"]] = p["expiration_timestamp_ms"]
		for k in self.seen:
			if self.seen[k] - now > 15*60*1000:
				del self.seen[k]
	
	def print_pokemon(self, locname, pokemon, now):
		def strftime(ts):
			return time.strftime("%H:%M:%S", time.localtime(ts / 1000))
		toPrint = []
		for p in pokemon:
			eid = p["encounter_id"]
			exp_ts = p["expiration_timestamp_ms"]
			seen = self.seen.get(eid, None)
			if seen == None or (seen == -1 and exp_ts != -1):
				name = POKEMON_NAMES[p["pokemon_id"]]
				exp = strftime(exp_ts) if exp_ts != -1 else ">" + strftime(now + 15 * 60 * 1000)
				if not print_coords:
					toPrint.append("%s (%s)" % (name, exp))
				else:
					toPrint.append("%s (%s, [%.4f %.4f])" % (name, exp, p["latitude"], p["longitude"]))
		if len(toPrint):
			print("%s %s: %s" % (strftime(now), locname, ", ".join(toPrint)))

	def scan(self, api, locname, lat, lng):
		pokemon, now = self.get_pokemon(api, lat, lng)
		self.print_pokemon(locname, pokemon, now)
		self.update(pokemon, now)

_print = print
def print(*args, **kwargs):
	_print(*args, **kwargs)
	sys.stdout.flush()

try:
	scanner = PoGoScanner(login, locations)
	scanner.start()
	while True:
		scanner.event.set()
		time.sleep(scanner.delay)
except KeyboardInterrupt:
	print("Stopping (^C)")
