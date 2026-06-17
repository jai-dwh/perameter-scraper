from scraper.scraper import GoogleAIModeScraper

scraper = GoogleAIModeScraper(headless=True)

query=('''Rams Event alwar Price Range, Trust Rating & Reviews, Planning Speciality, Wedding Types Covered,Services Offered ,Destination Wedding Support ,Decoration Styles ,Cities Covered ,Guest & Hospitality Management, Entertainment Services and Address exclude the refrences of justdial and weddingwire''')

result = scraper.ask_ai_mode(query)
with open("output.txt","w") as f:
    f.write(str(result["answer"]))
print("==================")

print(result["answer"])