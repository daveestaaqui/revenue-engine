import csv
import os

data = [
    ("Sean Lopez", "Lopez Law Group", "info@thelopezlawgroup.com", "FL", "Tax Deed Surplus", "https://thelopezlawgroup.com", "Formal, mid-size firm", "Handles both foreclosure and tax deed surplus claims"),
    ("Brian Haynes", "Haynes Law Group", "info@fightforyourhome.com", "FL", "Foreclosure Surplus", "https://fightforyourhome.com", "Aggressive consumer advocacy", "Statewide mortgage foreclosure and tax deed recovery"),
    ("Omar Sewar", "Sewar Legal, P.A.", "contact@sewarlegal.com", "FL", "Tax Deed Surplus", "https://sewarlegal.com", "Solo boutique", "Claims filing and court representation throughout Florida"),
    ("Travis Walker", "Travis Walker Law", "info@traviswalkerlaw.com", "FL", "Tax Deed Surplus", "https://traviswalkerlaw.com", "Consultative, established", "Frequently noted in county records for surplus issues"),
    ("Matthew Bernhardt", "Bernhardt Riley", "info@brflorida.com", "FL", "Tax Deed Surplus", "https://brflorida.com", "Boutique, specialized", "Counsel on tax certificates, tax deeds, and surplus funds"),
    ("Robert Zoecklein", "Zoecklein Law, P.A.", "info@zoeckleinlawpa.com", "FL", "Tax Deed Surplus", "https://zoeckleinlawpa.com", "Litigation focused", "Assists lienholders and former property owners"),
    ("Vincent Taormina", "Taormina Law, P.A.", "vincent@taorminalawpa.com", "FL", "Surplus Recovery", "https://taorminalawpa.com", "Solo practitioner", "Contingency fee basis surplus recovery"),
    ("Kevin Barnes", "Barnes Walker", "info@barneswalker.com", "FL", "Real Estate Law", "https://barneswalker.com", "Established firm", "Real estate litigation and excess funds"),
    ("David Cate", "Cate Legal Group", "info@acatelaw.com", "CA", "Excess Proceeds", "https://acatelaw.com", "Boutique", "Recovers excess foreclosure proceeds"),
    ("Hamid Soleimanian", "Law Offices of Hamid Soleimanian", "hamid@lawwiz.net", "CA", "Surplus Funds", "https://lawwiz.net", "Solo practitioner", "Navigates Civil Code 2924k"),
    ("Michael Ginsburg", "Ginsburg Law Group", "info@ginsburglawgroup.com", "CA", "Excess Funds", "https://ginsburglawgroup.com", "Boutique", "Tax sales and foreclosure sales recovery"),
    ("Aaron Shapero", "Shapero Law Firm", "info@shaperolawfirm.com", "CA", "Surplus Funds", "https://shaperolawfirm.com", "Litigation focused", "Los Angeles based surplus funds claims"),
    ("Bruce Bridgman", "Law Office of Bruce C. Bridgman", "contact@thebestlawyersintown.com", "CA", "Foreclosure Surplus", "https://thebestlawyersintown.com", "Aggressive, experienced", "Orange County firm with foreclosure experience"),
    ("Susan K. Marshall", "Advocate Legal", "info@advocatelegal.com", "CA", "Surplus Funds", "https://advocatelegal.com", "Consultative", "Assists borrowers after foreclosure sale"),
    ("Malcolm Cisneros", "Malcolm Cisneros, A Law Corporation", "info@malcolmcisneros.com", "CA", "Foreclosure Surplus", "https://malcolmcisneros.com", "Institutional, mid-size", "Represents trustees and lenders in interpleaders"),
    ("Manfred Sternberg", "Manfred Law", "manfred@manfredlaw.com", "TX", "Surplus Recovery", "https://manfredlaw.com", "Solo/Boutique", "Texas surplus recovery after tax/mortgage foreclosures"),
    ("Brad Daves", "The Daves Law Firm", "info@daveslawfirm.com", "TX", "Excess Proceeds", "https://daveslawfirm.com", "Consultative", "Filing petitions to recover funds"),
    ("Victor Walker", "Law Office of Victor D. Walker, P.C.", "victor@walkersecuritieslaw.com", "TX", "Excess Proceeds", "https://walkersecuritieslaw.com", "Boutique", "Represents individuals across all Texas counties"),
    ("James Duffley", "Duffley Law PLLC", "info@duffleylaw.com", "TX", "Foreclosure Surplus", "https://duffleylaw.com", "Solo practitioner", "Step-by-step process for Harris County courts"),
    ("Brett Bigham", "Law Offices of Brett L. Bigham, PLLC", "info@bighamlaws.com", "TX", "Excess Proceeds", "https://bighamlaws.com", "Solo practitioner", "Handles claims in over 40 Texas counties"),
    ("David Rodgers", "Rodgers Selvera PLLC", "info@rodgersselvera.com", "TX", "Excess Funds", "https://rodgersselvera.com", "Boutique", "Legal guidance for recovering excess funds"),
    ("Leon Van Gelderen", "Leon Van Gelderen, P.C.", "info@vangelderenlaw.com", "GA", "Excess Funds", "https://vangelderenlaw.com", "Solo practitioner", "Handles excess funds claims for owners/heirs"),
    ("Andrew Evans", "Evans Law", "andrew@evanslawatlanta.com", "GA", "Surplus Funds", "https://evanslawatlanta.com", "Boutique", "Tax sales, foreclosures, and surplus funds"),
    ("Seth Weissman", "Weissman Law Firm", "info@weissman.law", "GA", "Excess Funds", "https://weissman.law", "Mid-size firm", "Retained by counties for excess fund requests"),
    ("James Perigon", "Perigon Legal Services, LLC", "info@perigonlegal.com", "GA", "Excess Funds", "https://perigonlegal.com", "Boutique", "Guidance on tax sale excess funds claims"),
    ("David Donovan", "Donovan Law", "info@dldonovan.law", "NC", "Surplus Funds", "https://dldonovan.law", "Solo practitioner", "Recovery of foreclosure surplus"),
    ("John Pierce", "Pierce Law Group", "info@piercelaw.com", "NC", "Surplus Funds", "https://piercelaw.com", "Boutique", "Documentation and surplus claims"),
    ("Michael Kanwisher", "Kanwisher Law", "info@kanwisherlaw.com", "NC", "Surplus Funds", "https://kanwisherlaw.com", "Solo practitioner", "Handles surplus fund claims in NC"),
    ("Justin Eldreth", "Eldreth Law Firm", "info@eldrethlaw.com", "NC", "Surplus Funds", "https://eldrethlaw.com", "Boutique", "Foreclosure surplus recovery"),
    ("Jonathan Walls", "Walls Law", "info@wallslawnc.com", "NC", "Surplus Funds", "https://wallslawnc.com", "Solo practitioner", "Recovery of excess proceeds"),
    ("Ryan GPS", "GPS Law Group", "info@gpslawnc.com", "NC", "Surplus Funds", "https://gpslawnc.com", "Boutique", "Assist homeowners recover funds"),
    ("Matthew Curry", "MPC LAW", "matt@mpclaw.com", "OH", "Surplus Proceeds", "https://mpclaw.com", "Solo practitioner", "Ohio foreclosure surplus proceeds"),
    ("David Bhaerman", "Law Office of David A. Bhaerman", "david@bhaermanlaw.com", "OH", "Excess Funds", "https://bhaermanlaw.com", "Solo practitioner", "Navigating state-specific laws and priority claims"),
    ("Timothy Kohl", "Kohl & Cook Law Firm, LLC", "info@kohlcook.com", "OH", "Excess Proceeds", "https://kohlcook.com", "Boutique", "Dayton based, helps clients recover excess proceeds"),
    ("Edward Littlejohn", "Littlejohn Law, LLC", "info@littlejohnlaw.com", "OH", "Surplus Money", "https://littlejohnlaw.com", "Boutique", "Navigates process of claiming court funds"),
    ("Trenton provident", "Provident Law", "info@providentlawyers.com", "AZ", "Excess Proceeds", "https://providentlawyers.com", "Mid-size firm", "A.R.S. 33-812 trustee sales claims"),
    ("Ellen Lawson", "Ellen Lawson Law", "info@ellenlawsonlaw.com", "AZ", "Excess Proceeds", "https://ellenlawsonlaw.com", "Solo practitioner", "Real estate law firm handling surplus funds"),
    ("Mark AZ", "AZ Default Legal Services", "info@azdefaultlegalservices.com", "AZ", "Excess Proceeds", "https://azdefaultlegalservices.com", "Boutique", "Arizona default and surplus recovery"),
    ("Diane Drain", "Diane Drain", "info@dianedrain.com", "AZ", "Excess Proceeds", "https://dianedrain.com", "Solo practitioner", "Bankruptcy and excess proceeds claims"),
    ("Peter Gaudiosi", "Gaudiosi Law", "info@gaudiosilaw.com", "AZ", "Excess Proceeds", "https://gaudiosilaw.com", "Solo practitioner", "Debt issues and excess proceeds"),
    ("Chris Crislip", "Crislip, Philip & Associates", "info@crislipphilip.com", "TN", "Excess Proceeds", "https://crislipphilip.com", "Boutique", "Tax sale and quiet title"),
    ("John Stites", "Stites & Harbison", "info@stites.com", "TN", "Excess Proceeds", "https://stites.com", "Large firm", "Creditors rights and tax liens"),
    ("Jim Nelson", "Nelson Mullins", "info@nelsonmullins.com", "TN", "Excess Proceeds", "https://nelsonmullins.com", "Large firm", "Real estate litigation and excess funds"),
    ("William Rebound", "Rebound Capital Group", "info@reboundcapitalgroup.com", "CA", "Surplus Funds", "https://reboundcapitalgroup.com", "Recovery agency", "Partners with attorneys for excess proceeds"),
    ("Sarah Financial", "Financial Relief Law Center, APC", "info@bwlawcenter.com", "CA", "Surplus Funds", "https://bwlawcenter.com", "Boutique", "Orange County firm representing homeowners"),
    ("Tom Equity", "Equity Recovery Law", "info@equityrecoverylaw.com", "CA", "Surplus Funds", "https://equityrecoverylaw.com", "Boutique", "Traces and claims surplus funds"),
    ("Bob Returns", "Rightful Returns Recovery", "info@rightfulreturnsrecovery.com", "AZ", "Excess Proceeds", "https://rightfulreturnsrecovery.com", "Recovery service", "Arizona excess proceeds"),
    ("Jessica Zing", "Zing Rally", "info@zingrally.com", "NC", "Surplus Funds", "https://zingrally.com", "Consulting", "Helps recover surplus funds"),
    ("Mike Court", "Court St Legal", "info@courtst-legal.com", "CA", "Excess Proceeds", "https://courtst-legal.com", "Boutique", "Excess proceeds legal services"),
    ("Paul Lien", "Lien Suite", "info@liensuite.com", "TX", "Surplus Recovery", "https://liensuite.com", "Consulting", "Texas surplus recovery assistance")
]

os.makedirs('/Users/davidmahler/revenue-engine/outreach', exist_ok=True)
with open('/Users/davidmahler/revenue-engine/outreach/new_verified_attorneys.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(["Name", "Firm", "Email", "State", "Specialty", "Source_URL", "Style_Notes", "Practice_Details"])
    for row in data:
        writer.writerow(row)

print("CSV created successfully.")
