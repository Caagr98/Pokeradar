#!/usr/bin/env python3
locations = [
	("Eivind",	57.796581, 11.750235),
	("Morgan", 57.793591, 11.744238),
	("Rorvik", 57.791412, 11.753153),
	("Karholmen", 57.795726, 11.761720),
	("Bastovagen", 57.800572, 11.749605),
	("Vrakarr", 57.801681, 11.752957),
	("Vrakarr NE", 57.801807, 11.754631),
]
login = ( "ptc", "ezpex3", "reeper47" )

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
parser = argparse.ArgumentParser()
parser.add_argument("-v", "--verbose", help="spam a lot of debug info", action="store_true")
parser.add_argument("-n", "--nidoran", help="replace Nidoran's suffixes with [MF], to help non-Unicode-aware terminals", action="store_true")
args = parser.parse_args()

if args.verbose:
	import logging
	logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(module)10s] [%(levelname)5s] %(message)s')
	logging.getLogger("requests").setLevel(logging.WARNING)
	logging.getLogger("pgoapi").setLevel(logging.INFO)
	logging.getLogger("rpc_api").setLevel(logging.INFO)
if args.nidoran:
	POKEMON_NAMES[29] = "Nidoran F"
	POKEMON_NAMES[32] = "Nidoran M"

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
		print("Logging in")
		self.api = pgoapi.PGoApi(provider=login[0], username=login[1], password=login[2])
		print("Logged in")
		self.api.activate_signature(get_encrypt_lib())
		self.event = threading.Event()
		self.seen = {}
		self.locs = itertools.cycle(locations)

	def run(self):
		self.running = True
		while self.running:
			self.event.wait()
			self.event.clear()
			self.scan(*next(self.locs))

	def get_pokemon(self, lat, lng):
		self.api.set_position(lat, lng, 40)
		cells = pgoutil.get_cell_ids(lat, lng, 70)
		r = self.api.get_map_objects(since_timestamp_ms=[0] * len(cells), cell_id=cells)["responses"]["GET_MAP_OBJECTS"]
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
				toPrint.append("%s (%s)" % (name, exp))
		if len(toPrint):
			print("%s %s: %s" % (strftime(now), locname, ", ".join(toPrint)))

	def scan(self, locname, lat, lng):
		pokemon, now = self.get_pokemon(lat, lng)
		self.print_pokemon(locname, pokemon, now)
		self.update(pokemon, now)

try:
	scanner = PoGoScanner(login, locations)
	scanner.start()
	while True:
		scanner.event.set()
		time.sleep(5)
except KeyboardInterrupt:
	pass
