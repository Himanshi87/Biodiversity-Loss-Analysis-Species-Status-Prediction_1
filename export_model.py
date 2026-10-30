"""Train the project's Random Forest and export it for the website.
Run from the biodiversity_app folder:  python export_model.py
Uses data/Markov*.xlsx if present, otherwise synthetic DEMO data (flagged on the site)."""
import json
from pathlib import Path
from core import classifier as clf
from core.constants import STATES
from core.data_loader import find_file, read_any, parse_status_changes
from core.demo_data import demo_status_changes

ROOT = Path(__file__).parent
# Curated well-known species: (scientific, common, group, status). Verify against iucnredlist.org before relying on them.
CURATED = [
 ("Ailuropoda melanoleuca","Giant Panda","MAMMALIA","VU"),("Panthera tigris","Tiger","MAMMALIA","EN"),
 ("Panthera uncia","Snow Leopard","MAMMALIA","VU"),("Panthera leo","Lion","MAMMALIA","VU"),
 ("Acinonyx jubatus","Cheetah","MAMMALIA","VU"),("Elephas maximus","Asian Elephant","MAMMALIA","EN"),
 ("Loxodonta africana","African Savanna Elephant","MAMMALIA","EN"),("Loxodonta cyclotis","African Forest Elephant","MAMMALIA","CR"),
 ("Balaenoptera musculus","Blue Whale","MAMMALIA","EN"),("Diceros bicornis","Black Rhinoceros","MAMMALIA","CR"),
 ("Rhinoceros unicornis","Indian Rhinoceros","MAMMALIA","VU"),("Pongo abelii","Sumatran Orangutan","MAMMALIA","CR"),
 ("Ursus maritimus","Polar Bear","MAMMALIA","VU"),("Vulpes vulpes","Red Fox","MAMMALIA","LC"),
 ("Canis lupus","Grey Wolf","MAMMALIA","LC"),("Giraffa camelopardalis","Giraffe","MAMMALIA","VU"),
 ("Pan troglodytes","Chimpanzee","MAMMALIA","EN"),("Phocoena sinus","Vaquita","MAMMALIA","CR"),
 ("Haliaeetus leucocephalus","Bald Eagle","AVES","LC"),("Falco peregrinus","Peregrine Falcon","AVES","LC"),
 ("Pavo cristatus","Indian Peafowl","AVES","LC"),("Ardeotis nigriceps","Great Indian Bustard","AVES","CR"),
 ("Strigops habroptilus","Kakapo","AVES","CR"),("Raphus cucullatus","Dodo","AVES","EX"),
 ("Gavialis gangeticus","Gharial","REPTILIA","CR"),("Eretmochelys imbricata","Hawksbill Sea Turtle","REPTILIA","CR"),
 ("Chelonia mydas","Green Sea Turtle","REPTILIA","EN"),("Dermochelys coriacea","Leatherback Sea Turtle","REPTILIA","VU"),
 ("Varanus komodoensis","Komodo Dragon","REPTILIA","EN"),("Incilius periglenes","Golden Toad","AMPHIBIA","EX"),
]
THREATS = {
 "Panthera tigris":["Poaching for skins and bones","Habitat loss and fragmentation","Loss of prey species","Human-wildlife conflict"],
 "Diceros bicornis":["Poaching for horn","Illegal wildlife trade","Habitat loss"],
 "Loxodonta cyclotis":["Poaching for ivory","Forest loss and fragmentation","Bushmeat hunting"],
 "Loxodonta africana":["Poaching for ivory","Habitat loss","Human-elephant conflict"],
 "Elephas maximus":["Habitat loss and fragmentation","Human-elephant conflict","Poaching"],
 "Pongo abelii":["Deforestation (palm oil, logging)","Illegal pet trade","Hunting and conflict"],
 "Pan troglodytes":["Habitat loss","Hunting for bushmeat","Disease"],
 "Balaenoptera musculus":["Ship strikes","Entanglement in fishing gear","Ocean noise","Historic whaling"],
 "Phocoena sinus":["Bycatch in gillnets (illegal totoaba fishing)","Extremely small population"],
 "Ardeotis nigriceps":["Collisions with power lines","Grassland habitat loss","Hunting and disturbance"],
 "Strigops habroptilus":["Introduced predators (cats, stoats, rats)","Very small population","Low genetic diversity"],
 "Gavialis gangeticus":["River damming and sand mining","Fishing-net entanglement","Habitat loss"],
 "Eretmochelys imbricata":["Illegal shell trade","Egg harvesting","Loss of nesting beaches and coral reefs","Fisheries bycatch"],
 "Chelonia mydas":["Fisheries bycatch","Egg and turtle harvesting","Nesting-habitat loss","Climate change"],
 "Varanus komodoensis":["Climate change and sea-level rise","Habitat loss","Loss of prey"],
}
MEASURES = {
 "Panthera tigris":["Strengthen anti-poaching patrols and wildlife-crime enforcement","Protect and connect forest corridors","Restore prey populations","Support community programmes that reduce conflict"],
 "Diceros bicornis":["Ranger protection and intelligence-led anti-poaching","Move animals to secure reserves to grow populations","Reduce demand for horn and close illegal markets"],
 "Loxodonta cyclotis":["Enforce ivory-trade bans and stop poaching","Protect intact forest and corridors","Reduce bushmeat hunting through alternative livelihoods"],
 "Loxodonta africana":["Anti-poaching and ivory-trade enforcement","Secure migration corridors","Fund conflict mitigation such as beehive fences"],
 "Elephas maximus":["Protect and connect forest habitat","Early-warning systems and barriers to reduce crop-raiding conflict","Anti-poaching enforcement"],
 "Pongo abelii":["Stop forest clearing and promote deforestation-free palm oil","Enforce pet-trade laws; rescue and rehabilitate orangutans","Restore forest corridors"],
 "Pan troglodytes":["Protect forest habitat and corridors","Enforce hunting bans and promote alternative protein sources","Disease monitoring and veterinary care in protected areas"],
 "Balaenoptera musculus":["Shipping-lane changes and speed limits to reduce ship strikes","Whale-safe fishing gear","Reduce ocean noise","Enforce the whaling ban"],
 "Phocoena sinus":["Enforce the gillnet ban and remove ghost nets","Promote vaquita-safe fishing gear","Combat illegal totoaba trade"],
 "Ardeotis nigriceps":["Bury or mark power lines in key habitat","Protect grasslands and run captive breeding","Reduce hunting and disturbance"],
 "Strigops habroptilus":["Predator-free island sanctuaries","Intensive nest protection and supplementary feeding","Genetic management and assisted breeding"],
 "Gavialis gangeticus":["Protect nesting sandbanks and river flows","Regulate sand mining and fishing nets","Captive-rearing and release programmes"],
 "Eretmochelys imbricata":["Ban shell trade and enforce CITES","Protect nesting beaches and coral reefs","Turtle-excluder devices and bycatch reduction"],
 "Chelonia mydas":["Protect nesting beaches and stop egg harvesting","Reduce bycatch with turtle-excluder devices","Reduce plastic pollution"],
 "Varanus komodoensis":["Protect habitat and prey","Manage tourism and settlement","Monitor climate and sea-level impacts and plan refuges"],
}
f = find_file(ROOT / "data", ["Markov*.xlsx", "Markov*.xls"])
if f:
    species, _ = parse_status_changes(read_any(f.read_bytes(), f.name)); demo = False
else:
    species = demo_status_changes(); demo = True
b = clf.train_random_forest(species)
model = {}
for g in list(b["taxonomies"]) + ["__unseen__"]:
    model[g] = {s: {r["IUCN status"]: round(float(r["Probability"]), 6) for _, r in clf.predict_status(b, g, s)["table"].iterrows()} for s in STATES}
db = {} if demo else {r["Scientific name"]: [r["Scientific name"], str(r["Common name"]) if r["Common name"] == r["Common name"] else "", r["Taxonomy"], r["Status_2021"], r["Status_2022"]] for _, r in species.iterrows()}
for sci, com, grp, st in CURATED:
    db.setdefault(sci, [sci, com, grp, st, ""])
for v in db.values():
    v.append(THREATS.get(v[0], []))
    v.append(MEASURES.get(v[0], []))
out = {"demo": demo, "groups": b["taxonomies"], "model": model, "species": sorted(db.values(), key=lambda x: x[0])}
Path(ROOT / "biodiversity_website" / "data.js").write_text(
    "var BIO = " + json.dumps(out, ensure_ascii=False) + ";\nif (typeof module !== 'undefined') module.exports = BIO;\n", encoding="utf-8")
print("Exported", "DEMO" if demo else "REAL", "model:", len(out["species"]), "species,", len(out["groups"]), "groups")
