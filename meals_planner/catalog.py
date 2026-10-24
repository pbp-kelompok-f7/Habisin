"""Starter recipes until the recipe discovery catalogue is connected."""

RECIPES = {
    "chicken-soup": {
        "name": "Sup Ayam Wortel Kentang",
        "minutes": 30,
        "image": "home/img/r1.png",
        "ingredients": ["ayam", "wortel", "kentang", "bawang putih", "seledri"],
    },
    "fried-rice": {
        "name": "Nasi Goreng Sisa Sayur",
        "minutes": 20,
        "image": "home/img/r2.png",
        "ingredients": ["nasi", "wortel", "telur", "bawang putih", "kecap manis"],
    },
    "spinach-omelet": {
        "name": "Omelet Bayam Keju",
        "minutes": 15,
        "image": "home/img/r3.png",
        "ingredients": ["telur", "bayam", "keju"],
    },
}

DAYS = [
    ("Sen", "Senin"), ("Sel", "Selasa"), ("Rab", "Rabu"),
    ("Kam", "Kamis"), ("Jum", "Jumat"), ("Sab", "Sabtu"), ("Min", "Minggu"),
]
SLOTS = [("breakfast", "Sarapan"), ("lunch", "Makan Siang"), ("dinner", "Makan Malam")]
