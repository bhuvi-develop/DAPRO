"""Synthetic, fictional reference data for the DEMO tenant. No real persons or institutions."""
import random

RNG = random.Random(20261106)

FIRST_M = ["Arun", "Karthik", "Vignesh", "Suresh", "Rahul", "Aravind", "Harish", "Pranav", "Dinesh", "Gokul",
           "Naveen", "Ashwin", "Bharath", "Sanjay", "Vikram", "Manoj", "Rohit", "Siddharth", "Varun", "Ajay",
           "Hari", "Kiran", "Mohan", "Nikhil", "Praveen", "Ramesh", "Sathish", "Tarun", "Venkat", "Yash"]
FIRST_F = ["Priya", "Meena", "Divya", "Lakshmi", "Kavya", "Anitha", "Deepa", "Swathi", "Nithya", "Revathi",
           "Sneha", "Pooja", "Aishwarya", "Harini", "Janani", "Keerthana", "Madhumitha", "Nandhini", "Ramya",
           "Sandhya", "Shruthi", "Uma", "Vaishnavi", "Yamini", "Abirami", "Bhavana", "Gayathri", "Indhu", "Kalpana",
           "Lavanya"]
LAST = ["Krishnan", "Raman", "Subramanian", "Natarajan", "Venkatesan", "Raghavan", "Srinivasan", "Iyer",
        "Pillai", "Murugan", "Selvam", "Ganesan", "Chandran", "Balaji", "Kumar", "Rajendran", "Sundaram",
        "Arumugam", "Palani", "Mohan", "Shankar", "Gopal", "Nair", "Menon", "Reddy", "Rao", "Prakash", "Anand",
        "Babu", "Elango"]

CITIES_TN = [("Chennai", "Tamil Nadu", "6000"), ("Coimbatore", "Tamil Nadu", "6410"), ("Madurai", "Tamil Nadu", "6250"),
             ("Tiruchirappalli", "Tamil Nadu", "6200"), ("Salem", "Tamil Nadu", "6360"), ("Erode", "Tamil Nadu", "6380"),
             ("Vellore", "Tamil Nadu", "6320"), ("Tirunelveli", "Tamil Nadu", "6270")]
CITIES_IN = [("Bengaluru", "Karnataka", "5600"), ("Hyderabad", "Telangana", "5000"), ("Pune", "Maharashtra", "4110"),
             ("Mumbai", "Maharashtra", "4000")]
CITIES_ABROAD = [("Austin", "Texas", "78701", "US"), ("London", "England", "EC1A", "GB"),
                 ("Munich", "Bavaria", "80331", "DE"), ("Melbourne", "Victoria", "3000", "AU"),
                 ("Toronto", "Ontario", "M5H", "CA")]
STREETS = ["Gandhi Road", "Nehru Street", "Kamarajar Salai", "Bharathi Nagar", "Anna Salai", "Lake View Road",
           "Temple Street", "Station Road", "Park Avenue", "Gardens Main Road", "Market Street", "College Road"]

PROGRAMMES = [("B.E.", "Computer Science and Engineering", 4), ("B.E.", "Electronics and Communication", 4),
              ("B.Tech", "Information Technology", 4), ("B.E.", "Mechanical Engineering", 4),
              ("M.B.A.", "Business Administration", 2), ("M.Tech", "Data Science", 2), ("M.C.A.", "Computer Applications", 2),
              ("B.E.", "Civil Engineering", 4)]
EMPLOYERS = [("Northwind Software Services", "IT Services"), ("Kaveri Analytics", "Analytics"),
             ("Bluepeak Engineering", "Manufacturing"), ("Lotus Health Systems", "Healthcare"),
             ("Coastal Logistics", "Logistics"), ("Granite Fintech Labs", "Financial Services"),
             ("Silverline Automotive", "Automotive"), ("Banyan Consulting", "Consulting")]
JOBS = ["Software Engineer", "Analyst", "Graduate Engineer Trainee", "Associate Consultant", "Design Engineer",
        "Data Analyst", "Business Analyst", "Site Engineer", "Product Associate", "QA Engineer"]
RELATIONS = ["Father", "Mother", "Uncle", "Elder Brother", "Guardian"]


def person(gender: str | None = None) -> tuple[str, str, str]:
    g = gender or RNG.choice(["M", "F"])
    first = RNG.choice(FIRST_M if g == "M" else FIRST_F)
    return first, RNG.choice(LAST), g


def mobile() -> str:
    return "+91" + str(RNG.choice([6, 7, 8, 9])) + "".join(str(RNG.randint(0, 9)) for _ in range(9))


def norm_name(s: str) -> str:
    return " ".join(sorted(s.upper().replace(".", " ").split()))
