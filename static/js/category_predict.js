// ===== ENHANCED CATEGORY DATASET =====
const defaultCategoryDataset = {
    "Food & Dining": {
        "keywords": [
            // Restaurants & Cafes
            "restaurant", "cafe", "dinner", "lunch", "breakfast", "brunch", "supper",
            "food", "meal", "dining", "eat", "cuisine", "bistro", "grill", "buffet",
            
            // Food Delivery Platforms
            "zomato", "swiggy", "ubereats", "doordash", "foodpanda", "grubhub",
            "deliveroo", "eatclub", "faasos", "box8", "freshmenu", "eatfit",
            
            // Fast Food Chains
            "mcdonald's", "mcd", "kfc", "burger king", "domino's", "pizza hut",
            "subway", "taco bell", "wendy's", "chipotle", "dunkin", "starbucks",
            "costa coffee", "barista", "ccd", "cafe coffee day", "chaayos",
            
            // Indian Fast Food
            "haldiram's", "bikanervala", "sagar ratna", "saravana bhavan",
            "annapoorna", "adyar ananda bhavan", "kanti sweets", "gangotri",
            
            // Groceries & Supermarkets
            "grocery", "groceries", "supermarket", "mart", "big basket", "grofers",
            "milk", "bread", "eggs", "vegetables", "fruits", "meat", "fish",
            "chicken", "mutton", "eggs", "dairy", "cheese", "butter", "yogurt",
            
            // Specific Items
            "pizza", "burger", "sandwich", "wrap", "taco", "burrito", "pasta",
            "noodles", "fried rice", "biryani", "dosa", "idli", "vada", "sambar",
            "chole bhature", "chicken curry", "fish fry", "paneer", "naan",
            "roll", "kebab", "shawarma", "hummus", "falafel", "sushi", "ramen",
            
            // Beverages
            "coffee", "tea", "chai", "latte", "cappuccino", "espresso", "cold coffee",
            "juice", "smoothie", "milkshake", "soft drink", "soda", "cold drink",
            "coke", "pepsi", "fanta", "sprite", "maaza", "slice", "frooti",
            
            // Desserts
            "ice cream", "dessert", "cake", "pastry", "brownie", "cookie",
            "chocolate", "candy", "sweet", "mithai", "gulab jamun", "jalebi",
            "rasmalai", "kheer", "halwa", "ladoo", "barfi",
            
            // Mess & Canteen
            "mess", "canteen", "tiffin", "lunch box", "home food", "thali",
            
            // Alcohol
            "bar", "pub", "brewery", "wine", "beer", "cocktail", "liquor",
            "whiskey", "vodka", "rum", "gin", "spirits", "pub", "tavern"
        ],
    },
    
    "Transportation": {
        "keywords": [
            // Ride Hailing
            "uber", "ola", "lyft", "grab", "gojek", "did", "rapido", "bike taxi",
            "cab", "taxi", "auto", "rickshaw", "tuk tuk", "cycle rickshaw",
            
            // Public Transport
            "bus", "metro", "train", "local train", "suburban", "monorail",
            "tram", "ferry", "boat", "shuttle", "transit", "public transport",
            
            // Long Distance Travel
            "flight", "airplane", "aircraft", "air india", "indigo", "spicejet",
            "goair", "vistara", "airasia", "akasa air", "railway", "irctc",
            
            // Fuel & Vehicle
            "petrol", "diesel", "cng", "ev charging", "fuel", "gas station",
            "filling station", "oil change", "service", "maintenance", "repair",
            
            // Parking & Tolls
            "parking", "parking fee", "toll", "toll plaza", "fastag", "highway",
            
            // Vehicle Rentals
            "car rental", "bike rental", "cycle rental", "zoomcar", "drivezy",
            "revv", "myles", "eco", "on drive", "self drive",
            
            // Commute Passes
            "metro card", "bus pass", "travel card", "monthly pass",
            
            // Misc Transport
            "commute", "travel", "transport", "transit", "ride", "journey",
            "pickup", "drop", "airport", "railway station", "bus stand",
            "metro station", "terminal", "port", "harbour"
        ],
    },
    
    "Shopping": {
        "keywords": [
            // E-commerce Platforms
            "amazon", "flipkart", "myntra", "ajio", "nykaa", "purplle", "meesho",
            "snapdeal", "shopclues", "paytm mall", "tatacliq", "croma",
            
            // Electronics
            "reliance digital", "vijay sales", "poorvika", "sangeetha", "ezone",
            "electronics", "gadget", "mobile", "phone", "smartphone", "laptop",
            "tablet", "ipad", "computer", "desktop", "tv", "television", "speaker",
            "headphone", "earphone", "airpods", "smartwatch", "fitness band",
            
            // Fashion
            "clothes", "clothing", "apparel", "dress", "shirt", "t-shirt", "jeans",
            "trousers", "pants", "shorts", "skirt", "saree", "salwar", "lehenga",
            "kurta", "ethnic wear", "western wear", "footwear", "shoes", "sandals",
            "slippers", "boots", "sneakers", "accessories", "watch", "belt",
            "handbag", "purse", "wallet", "backpack", "luggage", "suitcase",
            
            // Beauty & Personal Care
            "cosmetics", "makeup", "skincare", "haircare", "perfume", "deodorant",
            
            // Home & Furniture
            "furniture", "home decor", "furnishings", "curtains", "bedding",
            "mattress", "pillow", "sofa", "table", "chair", "wardrobe",
            
            // Books & Stationery
            "book", "books", "stationery", "pen", "pencil", "notebook", "diary",
            "office supplies", "art supplies", "craft supplies",
            
            // Department Stores
            "big bazaar", "d mart", "more", "spencer's", "reliance fresh",
            "easyday", "star bazaar", "hypermarket", "supermarket",
            
            // Traditional Stores
            "saravana stores", "pothys", "chennai silks", "nalli silks", "rmkv",
            "khazana", "tanishq", "kalyan jewellers", "joyalukkas", "malabar",
            
            // Misc Shopping
            "mall", "market", "store", "shop", "retail", "outlet", "boutique",
            "purchase", "buy", "order", "checkout", "cart", "shopping"
        ],
    },
    
    "Entertainment": {
        "keywords": [
            // Movies & Cinema
            "movie", "cinema", "theatre", "theater", "film", "pvr", "inox", 
            "carnival", "imax", "bookmyshow", "paytm movies", "film ticket",
            "movie ticket", "matinee", "premiere", "3d movie", "4dx",
            
            // Streaming Services
            "netflix", "prime video", "amazon prime", "disney+", "hotstar",
            "sonyliv", "zee5", "voot", "mx player", "alt balaji", "eros now",
            "hulu", "hbo", "appletv", "youtube premium", "youtube music",
            
            // Music Streaming
            "spotify", "apple music", "gaana", "wynk music", "jiosaavn",
            "amazon music", "hungama", "tidal", "soundcloud",
            
            // Events & Recreation
            "concert", "live show", "music show", "standup", "comedy show",
            "theater play", "drama", "musical", "opera", "ballet", "symphony",
            "festival", "fair", "exhibition", "trade show", "convention",
            
            // Sports
            "sports", "game", "match", "tournament", "stadium", "arena",
            "cricket", "football", "soccer", "tennis", "badminton", "golf",
            "swimming", "gym", "fitness", "workout", "yoga", "zumba",
            
            // Gaming
            "gaming", "video game", "playstation", "xbox", "nintendo",
            "steam", "epic games", "xbox live", "playstation plus",
            "mobile game", "pubg", "free fire", "candy crush",
            
            // Amusement & Recreation
            "amusement park", "theme park", "water park", "adventure park",
            "zoo", "aquarium", "museum", "planetarium", "science center",
            "botanical garden", "national park", "beach", "resort",
            
            // Nightlife
            "club", "night club", "disco", "dance", "party", "nightlife",
            
            // Hobbies
            "hobby", "craft", "art", "photography", "painting", "pottery",
            
            // Misc Entertainment
            "entertainment", "recreation", "leisure", "fun", "outing",
            "weekend plan", "date night", "family outing", "picnic"
        ],
    },
    
    "Bills & Utilities": {
        "keywords": [
            // Utilities
            "electricity", "electricity bill", "power bill", "current bill",
            "water bill", "water charges", "gas bill", "cooking gas",
            "gas cylinder", "lpg", "indane", "bharat gas", "hp gas",
            
            // Telecom
            "mobile bill", "phone bill", "postpaid", "prepaid recharge",
            "airtel", "jio", "vi", "vodafone idea", "bsnl", "mtnl",
            "broadband", "wifi", "internet bill", "act fiber", "spectra",
            "jio fiber", "airtel broadband", "hathway", "den", "tata sky",
            "dish tv", "dth", "cable tv", "cable bill",
            
            // Rent & Housing
            "rent", "house rent", "apartment rent", "pg rent", "hostel fee",
            "maintenance", "society maintenance", "housing society",
            "property tax", "house tax", "municipal tax",
            
            // Loans & EMIs
            "emi", "loan emi", "home loan", "car loan", "personal loan",
            "education loan", "vehicle loan", "loan repayment",
            
            // Insurance
            "insurance", "health insurance", "life insurance", "car insurance",
            "bike insurance", "term insurance", "medical insurance",
            "lic", "insurance premium", "policy payment",
            
            // Subscriptions
            "subscription", "membership", "annual fee", "renewal",
            "amazon prime", "netflix subscription", "spotify premium",
            
            // Other Bills
            "bill payment", "utility bill", "regular payment", "monthly bill",
            "quarterly bill", "annual bill", "outstanding", "dues",
            "overdue", "pending payment", "autopay", "standing instruction"
        ],
    },
    
    "Healthcare": {
        "keywords": [
            // Medical Institutions
            "hospital", "clinic", "nursing home", "medical center",
            "apollo", "fortis", "max", "manipal", "medanta", "aiims",
            "columbia asia", "care hospital", "narayana health",
            
            // Pharmacy & Medicine
            "pharmacy", "medical store", "chemist", "drug store",
            "pharmeasy", "netmeds", "1mg", "medlife", "apollo pharmacy",
            "medplus", "guardian pharmacy", "wellness forever",
            
            // Doctors & Specialists
            "doctor", "physician", "specialist", "consultation", "clinic visit",
            "general physician", "dentist", "dental", "eye specialist",
            "ophthalmologist", "dermatologist", "pediatrician", "gynecologist",
            "orthopedic", "cardiologist", "neurologist", "psychiatrist",
            
            // Diagnostics
            "diagnostics", "lab test", "pathology", "blood test", "xray",
            "x-ray", "mri", "ct scan", "ultrasound", "ecg", "echo",
            "health checkup", "health package", "preventive health",
            
            // Treatments
            "treatment", "therapy", "physiotherapy", "occupational therapy",
            "speech therapy", "counseling", "psychotherapy", "rehabilitation",
            
            // Wellness
            "wellness", "fitness", "gym", "yoga", "meditation",
            "ayurveda", "homeopathy", "unani", "siddha", "naturopathy",
            "acupuncture", "chiropractic", "massage", "spa",
            
            // Specific Health Needs
            "vaccination", "vaccine", "covid test", "covid vaccine",
            "flu shot", "immunization", "health supplement", "vitamin",
            "protein powder", "nutrition", "dietary supplement",
            
            // Dental
            "dental cleaning", "root canal", "cavity filling", "crown",
            "braces", "orthodontic", "teeth whitening",
            
            // Eye Care
            "eye checkup", "spectacles", "glasses", "contact lens",
            "lens solution", "lasik", "eye surgery",
            
            // Mental Health
            "mental health", "therapy session", "counseling session",
            "psychologist", "psychiatrist", "mental wellness"
        ],
    },
    
    "Education": {
        "keywords": [
            // Educational Institutions
            "school", "college", "university", "institute", "academy",
            "preschool", "playschool", "kindergarten", "nursery school",
            "high school", "senior secondary", "pu college", "degree college",
            
            // Fees
            "tuition fee", "school fee", "college fee", "admission fee",
            "registration fee", "exam fee", "library fee", "lab fee",
            "hostel fee", "mess fee", "transport fee", "bus fee",
            
            // Coaching & Tuition
            "tuition", "coaching", "tutoring", "private tutor", "home tutor",
            "iit coaching", "neet coaching", "jee coaching", "cet coaching",
            
            // Coaching Centers
            "aakash", "fiitjee", "allen", "resonance", "bansal classes",
            "vidyamandir", "narayana", "chaitanya", "akash", "pace",
            
            // Online Learning
            "byju's", "vedantu", "unacademy", "coursera", "udemy",
            "skillshare", "edx", "khan academy", "extramarks", "toppr",
            "whitehat jr", "coding class", "online course", "elearning",
            
            // Books & Materials
            "books", "textbook", "reference book", "study material",
            "stationery", "notebook", "pen", "pencil", "geometry box",
            "school bag", "uniform", "school dress", "lab coat",
            
            // Exams & Tests
            "exam", "test", "assessment", "practice test", "mock test",
            "entrance exam", "competitive exam", "board exam", "final exam",
            
            // Higher Education
            "pg course", "masters", "phd", "doctorate", "diploma",
            "certification", "professional course", "executive education",
            
            // Workshops & Seminars
            "workshop", "seminar", "conference", "symposium", "webinar",
            "training", "certification program", "skill development",
            
            // Educational Resources
            "educational app", "learning app", "dictionary", "encyclopedia",
            "educational toy", "learning kit", "science kit",
            
            // Student Expenses
            "project work", "assignment", "printout", "photocopy",
            "project material", "craft material", "art material",
            
            // Misc Education
            "education", "learning", "studies", "academics", "student"
        ],
    },
    
    "Travel": {
        "keywords": [
            // Accommodation
            "hotel", "resort", "lodge", "inn", "guest house", "homestay",
            "airbnb", "booking.com", "oyo", "treebo", "fabhotels",
            "hostel", "backpacker hostel", "dormitory", "capsule hotel",
            
            // Travel Booking Platforms
            "makemytrip", "goibibo", "cleartrip", "yatra", "ease my trip",
            "ixigo", "travelguru", "agoda", "expedia", "booking.com",
            "trivago", "hotels.com", "tripadvisor", "skyscanner",
            
            // Flights
            "flight ticket", "air ticket", "airfare", "booking flight",
            "domestic flight", "international flight", "business class",
            "economy class", "flight booking", "airline ticket",
            
            // Trains
            "train ticket", "railway ticket", "irctc", "railway reservation",
            "sleeper class", "ac class", "rail pass", "indian railway",
            
            // Buses
            "bus ticket", "volvo bus", "ac bus", "ordinary bus", "redbus",
            "abhibus", "intrcity", "bus reservation", "private bus",
            
            // Cabs & Transfers
            "airport transfer", "airport taxi", "drop service", "pickup service",
            "sightseeing cab", "tour cab", "rental cab", "chauffeur",
            
            // Tours & Activities
            "tour package", "holiday package", "vacation package",
            "sightseeing tour", "city tour", "guided tour", "tour guide",
            "excursion", "day trip", "cruise", "boat tour", "safari",
            
            // Travel Essentials
            "passport", "visa", "visa fee", "passport fee", "travel insurance",
            "foreign exchange", "currency exchange", "travel card",
            
            // Luggage
            "luggage", "suitcase", "baggage", "travel bag", "backpack",
            
            // Destinations
            "hill station", "beach destination", "heritage site",
            "pilgrimage", "temple tour", "wildlife sanctuary",
            
            // Misc Travel
            "travel", "tour", "trip", "vacation", "holiday", "getaway",
            "journey", "expedition", "adventure", "exploration",
            "destination wedding", "honeymoon package"
        ],
    },
    
    "Investments & Savings": {
        "keywords": [
            // Stocks & Trading
            "stocks", "shares", "equity", "trading", "dem at account",
            "brokerage", "zerodha", "groww", "angel one", "upstox",
            "icici direct", "hdfc sec", "kotak securities", "motilal oswal",
            "share market", "stock market", "intraday", "delivery",
            
            // Mutual Funds
            "mutual fund", "mf investment", "sip", "systematic investment",
            "lumpsum", "etf", "index fund", "debt fund", "equity fund",
            
            // Fixed Income
            "fixed deposit", "fd", "recurring deposit", "rd", "ppf",
            "public provident fund", "epf", "provident fund", "vpf",
            "nsc", "national savings certificate", "post office saving",
            
            // Retirement
            "nps", "national pension system", "pension", "retirement fund",
            "annuity", "pension plan", "superannuation",
            
            // Crypto & Digital Assets
            "cryptocurrency", "bitcoin", "ethereum", "crypto", "blockchain",
            "coinbase", "wazirx", "coin dcx", "binance", "crypto trading",
            
            // Gold & Commodities
            "gold", "silver", "digital gold", "sgb", "sovereign gold bond",
            "commodity trading", "commodity market", "bullion",
            
            // Tax Saving
            "tax saving", "tax planning", "tax free bond", "infrastructure bond",
            "elss", "equity linked saving scheme", "tax saving fd",
            
            // Investment Platforms
            "investment app", "wealth management", "portfolio management",
            "pms", "roboadvisor", "financial advisor", "wealth advisor",
            
            // Savings
            "savings account", "savings deposit", "high interest savings",
            "salary account", "zero balance account",
            
            // Misc Investments
            "investment", "investing", "capital market", "wealth creation",
            "asset allocation", "diversification", "portfolio"
        ],
    },
    
    "Income": {
        "keywords": [
            // Salary
            "salary", "monthly salary", "payroll", "wages", "paycheck",
            "net salary", "gross salary", "basic pay", "take home",
            
            // Business Income
            "business income", "business profit", "professional fee",
            "consulting fee", "freelance income", "self employed income",
            "sole proprietorship", "partnership income",
            
            // Freelancing
            "freelance", "gig work", "upwork", "fiverr", "freelancer.com",
            "toptal", "guru", "people per hour", "freelance payment",
            
            // Investments Returns
            "dividend", "interest income", "capital gains", "trading profit",
            "stock profit", "mutual fund return", "fd interest",
            
            // Rental Income
            "rent received", "rental income", "property income", "lease income",
            
            // Other Income Sources
            "bonus", "incentive", "commission", "tips", "gratuity",
            "overtime pay", "holiday pay", "sick pay", "maternity pay",
            "pension income", "retirement income", "social security",
            
            // Side Hustles
            "side hustle", "part time income", "passive income",
            "affiliate income", "referral bonus", "cashback", "rewards",
            
            // Gifts & Donations
            "gift received", "gift money", "cash gift", "donation received",
            "inheritance", "settlement", "lottery", "prize money",
            
            // Refunds & Reimbursements
            "tax refund", "insurance claim", "medical claim", "expense reimbursement",
            "travel reimbursement", "petty cash reimbursement",
            
            // Misc Income
            "income", "earning", "revenue", "receipt", "credit", "deposit",
            "inward payment", "payment received", "money received"
        ],
    },
    
    "Transfer": {
        "keywords": [
            // Bank Transfers
            "bank transfer", "neft", "rtgs", "imps", "upi transfer",
            "online transfer", "fund transfer", "money transfer",
            
            // UPI Apps
            "google pay", "gpay", "phonepe", "paytm", "amazon pay",
            "bhim upi", "whatsapp pay", "mobikwik", "freecharge",
            
            // Wallet Transfers
            "wallet transfer", "wallet load", "wallet cash", "paytm wallet",
            "mobikwik wallet", "amazon pay wallet", "phonepe wallet",
            
            // Account Transfers
            "savings to current", "account transfer", "internal transfer",
            "self transfer", "own account transfer",
            
            // Peer to Peer
            "send money", "receive money", "friend payment", "split bill",
            "shared expense", "group payment", "collect money",
            
            // International Transfers
            "international transfer", "foreign transfer", "wire transfer",
            "swift transfer", "wise", "transferwise", "remitly",
            "western union", "moneygram", "ria money transfer",
            
            // Misc Transfers
            "transfer", "transaction", "payment", "remittance",
            "fund movement", "money movement", "account transfer"
        ],
    },
    
    "Other": {
        "keywords": [
            // Default catch-all - minimal keywords
            "other", "misc", "miscellaneous", "general", "various"
        ],
    }
};


/**
 * Detect category from expense description using enhanced keyword matching.
 *
 * @param {string} description - The expense description string
 * @returns {string} - Category name string. Defaults to "Other" if no match found.
 *
 * Enhanced matching logic:
 * 1. Convert description to lowercase and trim
 * 2. Loop through all categories (excluding "Other" first for better matching)
 * 3. For each category, check if any keyword exists in description
 * 4. Prioritize longer matches (whole words vs partial)
 * 5. Return first matching category
 * 6. If no match, return "Other"
 */
function detectCategory(description) {
    // Handle empty or invalid input
    if (!description || typeof description !== 'string') {
        return "Other";
    }

    // Convert to lowercase for case-insensitive matching
    const descriptionLower = description.toLowerCase().trim();

    if (!descriptionLower) {
        return "Other";
    }

    // Create a copy of categories without "Other" for priority matching
    const prioritizedCategories = { ...defaultCategoryDataset };
    delete prioritizedCategories["Other"];
    
    // First check all non-Other categories
    for (const [categoryName, categoryData] of Object.entries(prioritizedCategories)) {
        const keywords = categoryData.keywords || [];

        for (const keyword of keywords) {
            // Convert keyword to lowercase
            const keywordLower = keyword.toLowerCase();
            
            // Check for whole word match (surrounded by word boundaries)
            const wholeWordPattern = new RegExp(`\\b${keywordLower}\\b`, 'i');
            if (wholeWordPattern.test(descriptionLower)) {
                return categoryName;
            }
            
            // Fall back to includes() for partial matches
            if (descriptionLower.includes(keywordLower)) {
                return categoryName;
            }
        }
    }

    // Check "Other" category if needed
    if (defaultCategoryDataset["Other"]) {
        const otherKeywords = defaultCategoryDataset["Other"].keywords || [];
        for (const keyword of otherKeywords) {
            if (descriptionLower.includes(keyword.toLowerCase())) {
                return "Other";
            }
        }
    }

    // No match found - return "Other"
    return "Other";
}