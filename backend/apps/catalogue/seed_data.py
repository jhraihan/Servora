CATEGORIES = [
    (
        "Electrical", "zap",
        "Wiring, fixtures, switchboards and electrical faults.",
        [
            ("Ceiling fan installation", "fixed", 500, 1200, 60, "fan, ceiling fan, fan not working, fan noise, fan install, pakha"),
            ("Light fixture installation", "fixed", 300, 800, 45, "light, bulb, tube light, lamp, chandelier, light not working, fitting"),
            ("Switchboard repair", "fixed", 400, 1500, 60, "switch, socket, plug point, switchboard, board, spark, power point"),
            ("House wiring", "visit_quote", None, None, 480, "wiring, rewiring, new connection, cable, short circuit, line"),
            ("Electrical fault diagnosis", "visit_quote", 300, 600, 60, "no power, power cut, tripping, short circuit, current problem, shock, fault"),
            ("Voltage stabiliser installation", "fixed", 600, 1500, 90, "stabiliser, stabilizer, voltage, ips, surge"),
        ],
    ),
    (
        "Plumbing", "droplet",
        "Pipes, taps, tanks, bathroom and kitchen fittings.",
        [
            ("Tap repair or replacement", "fixed", 300, 800, 45, "tap, faucet, dripping, water leak, kol, tap leaking"),
            ("Pipe leak repair", "fixed", 500, 1500, 60, "leak, leaking pipe, burst pipe, water leak, seepage, drip, pipe"),
            ("Toilet repair", "fixed", 600, 2000, 90, "toilet, commode, flush, blockage, clogged, drain, bathroom"),
            ("Water tank cleaning", "fixed", 1500, 4000, 180, "tank, water tank, reservoir, tank clean, overhead tank"),
            ("Basin installation", "fixed", 800, 2000, 90, "basin, sink, wash basin, kitchen sink"),
            ("Bathroom fitting installation", "visit_quote", None, None, 240, "bathroom, shower, geyser fitting, sanitary, fittings"),
        ],
    ),
    (
        "AC & Refrigeration", "wind",
        "Air conditioners, refrigerators and freezers.",
        [
            ("AC servicing", "fixed", 1200, 2500, 90, "ac service, air conditioner, ac cleaning, ac not cooling, cooling, servicing"),
            ("AC gas refill", "fixed", 2500, 5000, 120, "gas refill, ac gas, refrigerant, not cooling, cooling problem, freon"),
            ("AC installation", "fixed", 2000, 4500, 180, "ac install, new ac, split ac, air conditioner install, mounting"),
            ("AC repair", "visit_quote", 500, 1000, 120, "ac repair, ac not cooling, ac not working, cooling problem, ac leaking, air conditioner"),
            ("Refrigerator repair", "visit_quote", 500, 1000, 90, "fridge, refrigerator, freezer, not cooling, cooling problem, fridge not working"),
            ("Deep freezer repair", "visit_quote", 600, 1200, 120, "freezer, deep freeze, not freezing, cooling problem"),
        ],
    ),
    (
        "Computer & IT", "monitor",
        "Laptops, desktops, printers and home networks.",
        [
            ("Laptop repair", "visit_quote", 500, 1200, 90, "laptop, computer, notebook, screen, keyboard, not starting, slow"),
            ("Desktop assembly", "fixed", 1000, 2500, 120, "desktop, pc build, computer assembly, cpu, custom pc"),
            ("Operating system installation", "fixed", 500, 1200, 90, "windows, os install, format, software install, reinstall"),
            ("Virus removal", "fixed", 500, 1000, 60, "virus, malware, hacked, slow computer, antivirus, pop ups"),
            ("Printer repair", "visit_quote", 400, 1000, 60, "printer, printing problem, scanner, cartridge, paper jam"),
            ("Wi-Fi setup and troubleshooting", "fixed", 500, 1500, 60, "wifi, wi-fi, internet, router, network, no internet, slow internet"),
        ],
    ),
    (
        "Painting", "paintbrush",
        "Interior and exterior painting and surface preparation.",
        [
            ("Interior wall painting", "visit_quote", None, None, 480, "paint, painting, wall paint, interior, colour, color, repaint"),
            ("Exterior painting", "visit_quote", None, None, 960, "paint, exterior, outside wall, building paint, weather coat"),
            ("Single room painting", "fixed", 3000, 8000, 480, "paint, room paint, bedroom paint, one room"),
            ("Wood polishing", "visit_quote", None, None, 240, "polish, wood, furniture polish, varnish, door polish"),
            ("Wall putty and preparation", "visit_quote", None, None, 360, "putty, plaster, wall preparation, crack, surface"),
        ],
    ),
    (
        "Cleaning", "sparkles",
        "Home, kitchen, bathroom and post-construction cleaning.",
        [
            ("Full home deep cleaning", "visit_quote", None, None, 480, "cleaning, deep clean, house cleaning, home cleaning, full clean"),
            ("Kitchen deep cleaning", "fixed", 2000, 4500, 180, "kitchen, kitchen clean, chimney, grease, oil cleaning"),
            ("Bathroom deep cleaning", "fixed", 1000, 2500, 120, "bathroom clean, toilet clean, tiles, washroom cleaning"),
            ("Sofa and carpet cleaning", "fixed", 1500, 4000, 150, "sofa, carpet, upholstery, couch, rug, shampoo"),
            ("Post-construction cleaning", "visit_quote", None, None, 600, "after construction, renovation clean, debris, dust cleaning"),
            ("Regular home cleaning", "hourly", 200, 400, 180, "maid, regular cleaning, housekeeping, daily cleaning, weekly"),
        ],
    ),
    (
        "Appliance Repair", "wrench",
        "Washing machines, ovens, water heaters and small appliances.",
        [
            ("Washing machine repair", "visit_quote", 500, 1200, 90, "washing machine, washer, not spinning, drainage, laundry machine"),
            ("Microwave oven repair", "visit_quote", 400, 1000, 60, "microwave, oven, not heating, magnetron"),
            ("Water heater repair", "visit_quote", 500, 1200, 90, "geyser, water heater, hot water, no hot water, heater"),
            ("Gas stove repair", "fixed", 400, 1000, 60, "stove, gas, burner, cooker, hob, flame, gas leak"),
            ("Electric oven repair", "visit_quote", 500, 1200, 90, "oven, electric oven, baking, not heating"),
        ],
    ),
    (
        "Car Mechanic", "car",
        "On-site car servicing, diagnostics and battery work.",
        [
            ("Car servicing at home", "fixed", 2000, 5000, 180, "car service, car, servicing, oil change, doorstep car"),
            ("Battery replacement", "fixed", 500, 1200, 45, "battery, car battery, not starting, jump start, dead battery"),
            ("Engine diagnostics", "visit_quote", 800, 1500, 90, "engine, check engine, car problem, diagnostics, scanning"),
            ("Brake repair", "visit_quote", None, None, 120, "brake, brake pad, braking, disc, squealing"),
            ("AC servicing (car)", "fixed", 1500, 3500, 120, "car ac, car cooling, vehicle ac, car air conditioner"),
        ],
    ),
]

DHAKA = {
    "name": "Dhaka",
    "lat": 23.8103, "lon": 90.4125,
    "thanas": [
        ("Dhanmondi", 23.7461, 90.3742, [
            ("Dhanmondi 27", 23.7508, 90.3706),
            ("Dhanmondi 32", 23.7538, 90.3776),
            ("Jigatola", 23.7395, 90.3762),
            ("Hazaribagh", 23.7331, 90.3650),
        ]),
        ("Gulshan", 23.7925, 90.4078, [
            ("Gulshan 1", 23.7808, 90.4142),
            ("Gulshan 2", 23.7947, 90.4143),
            ("Banani", 23.7936, 90.4005),
            ("Baridhara", 23.8041, 90.4213),
        ]),
        ("Mirpur", 23.8223, 90.3654, [
            ("Mirpur 1", 23.7986, 90.3537),
            ("Mirpur 10", 23.8069, 90.3686),
            ("Mirpur 12", 23.8277, 90.3673),
            ("Pallabi", 23.8257, 90.3639),
        ]),
        ("Uttara", 23.8759, 90.3795, [
            ("Uttara Sector 3", 23.8690, 90.3987),
            ("Uttara Sector 7", 23.8759, 90.3861),
            ("Uttara Sector 11", 23.8785, 90.3936),
            ("Uttara Sector 13", 23.8698, 90.3811),
        ]),
        ("Mohammadpur", 23.7657, 90.3588, [
            ("Mohammadpur Central", 23.7657, 90.3588),
            ("Shyamoli", 23.7746, 90.3654),
            ("Adabor", 23.7739, 90.3576),
            ("Lalmatia", 23.7538, 90.3679),
        ]),
        ("Bashundhara", 23.8199, 90.4265, [
            ("Bashundhara Block A", 23.8199, 90.4265),
            ("Bashundhara Block C", 23.8156, 90.4310),
            ("Bashundhara Block G", 23.8244, 90.4348),
        ]),
        ("Motijheel", 23.7330, 90.4172, [
            ("Motijheel Commercial", 23.7330, 90.4172),
            ("Arambagh", 23.7345, 90.4148),
            ("Paltan", 23.7361, 90.4133),
        ]),
        ("Old Dhaka", 23.7104, 90.4074, [
            ("Lalbagh", 23.7189, 90.3880),
            ("Sutrapur", 23.7089, 90.4187),
            ("Wari", 23.7169, 90.4200),
        ]),
    ],
}
