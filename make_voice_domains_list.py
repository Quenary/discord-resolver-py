regions = [
    "atlanta",
    "brazil", 
    "bucharest",
    "buenos-aires",
    "dubai", 
    "finland", 
    "frankfurt",
    "hongkong",
    "india", 
    "japan",
    "madrid",
    "milan",
    "newark",
    "rotterdam",
    "russia",
    "santa-clara",
    "santiago",
    "seattle",
    "singapore",
    "south-korea",
    "southafrica",
    "stage-scale",
    "stockholm",
    "sydney",
    "tel-aviv",
    "us-central",
    "us-east",
    "us-south",
    "us-west",
    "warsaw",
]
entries = 15000
baseDomain = "discord.gg"

with open('voice_domains_list.txt', 'w') as file:
    for reg in regions:
        for num in range(0, entries):
            dom = f"{reg}{num}.{baseDomain}\n"
            file.write(dom)