import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

def search_arxiv(query, max_results=10):
    escaped_query = urllib.parse.quote(query)
    url = f'http://export.arxiv.org/api/query?search_query=all:{escaped_query}&sortBy=submittedDate&sortOrder=desc&max_results={max_results}'
    
    try:
        response = urllib.request.urlopen(url)
        xml_data = response.read()
        root = ET.fromstring(xml_data)
        
        for entry in root.findall('{http://www.w3.org/2005/Atom}entry'):
            title = entry.find('{http://www.w3.org/2005/Atom}title').text.strip().replace('\n', ' ')
            published = entry.find('{http://www.w3.org/2005/Atom}published').text[:10]
            authors = [a.find('{http://www.w3.org/2005/Atom}name').text for a in entry.findall('{http://www.w3.org/2005/Atom}author')]
            link = entry.find('{http://www.w3.org/2005/Atom}id').text
            print(f'[{published}] {title} ({authors[0]} et al.)\nLink: {link}\n')
            
    except Exception as e:
        print(f'Error fetching: {e}')

search_arxiv('%22text-to-sql%22 AND %22agent%22', 5)
search_arxiv('%22text-to-sql%22 AND %22RAG%22', 5)
