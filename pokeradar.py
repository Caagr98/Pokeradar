#!/usr/bin/env python3
locations = [
	("Eivind",  57.796581, 11.750235),
	("Morgan", 57.793591, 11.744238),
	("Rörvik", 57.791412, 11.753153),
	("Karholmen", 57.795726, 11.761720),
	("Bastövägen", 57.800572, 11.749605),
	("Vråkärr", 57.801681, 11.752957),
	("Vråkärr NE", 57.801807, 11.754631),
]
login = ( "ptc", "ezpex3", "reeper47" )

POKEMON_NAMES = [ "MissingNo", "Bulbasaur", "Ivysaur", "Venusaur", "Charmander",
		"Charmeleon", "Charizard", "Squirtle", "Wartortle", "Blastoise",
		"Caterpie", "Metapod", "Butterfree", "Weedle", "Kakuna", "Beedrill",
		"Pidgey", "Pidgeotto", "Pidgeot", "Rattata", "Raticate", "Spearow",
		"Fearow", "Ekans", "Arbok", "Pikachu", "Raichu", "Sandshrew",
		"Sandslash", "Nidoran♀", "Nidorina", "Nidoqueen", "Nidoran♂",
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
import s2sphere

import threading
import itertools
import os.path
import time

def get_cells(lat, lng, meters):
	axis = s2sphere.LatLng.from_degrees(lat, lng).normalized().to_point()
	angle = s2sphere.Angle.from_degrees(meters / 40075017 * 360)
	region = s2sphere.Cap.from_axis_angle(axis, angle)
	coverer = s2sphere.RegionCoverer()
	coverer.min_level = 15
	coverer.max_level = 0
	return coverer.get_covering(region)

class PoGoScanner(threading.Thread):
	def __init__(self, login, locations):
		threading.Thread.__init__(self, daemon=True)
		print("Logging in")
		self.api = pgoapi.PGoApi(provider=login[0], username=login[1], password=login[2])
		print("Logged in")
		self.api.activate_signature(os.path.join(os.path.dirname(os.path.realpath(__file__)), "libencrypt.so"))
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
		cells = sorted(cell.id() for cell in get_cells(lat, lng, 70))
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
	
	def print_pokemon(self, pokemon, now):
		def strftime(ts):
			return time.strftime("%H:%M:%S", time.localtime(ts / 1000))
		toPrint = []
		for p in pokemon:
			eid = p["encounter_id"]
			exp_ts = p["expiration_timestamp_ms"]
			seen = self.seen.get(eid, None)
			if seen == None or (seen == -1 and exp_ts != -1):
				name = POKEMON_NAMES[p["pokemon_id"]]
				exp = strftime(exp_ts) if exp_ts != -1 else ">" + strftime(exp_ts + 15 * 60 * 1000)
				toPrint.append("%s (%s)" % (name, exp))
		if len(toPrint):
			print("%s %s: %s" % (time(now), locname, ", ".join(toPrint)))

	def scan(self, locname, lat, lng):
		pokemon, now = self.get_pokemon(lat, lng)
		self.print_pokemon(pokemon, now)
		self.update(pokemon, now)

try:
	scanner = PoGoScanner(login, locations)
	scanner.start()
	while True:
		scanner.event.set()
		time.sleep(5)
except KeyboardInterrupt:
	pass
