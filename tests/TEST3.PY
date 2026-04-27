import requests
from lxml import html
import time

def test_live_match_score():
    """
    test script to check if score elements are present in the html
    at request time.
    """
    
    print("=" * 60)
    print("🧪 TESTE: VERIFICAR ELEMENTO DE SCORE")
    print("=" * 60)
    
    # 1. fazer requisição direta com requests (sem cloudscraper)
    url = "https://www.hltv.org/matches"
    
    print(f"\n📡 fetching: {url}")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"✅ status: {response.status_code}")
        print(f"📦 content length: {len(response.content)} bytes")
        
        # 2. parsear o HTML
        tree = html.fromstring(response.content)
        
        # 3. procurar elementos de score
        print("\n🔍 procurando spans com class 'current-map-score'...")
        
        score_elements = tree.xpath("//span[contains(@class, 'current-map-score')]")
        
        print(f"✅ encontrados {len(score_elements)} elementos")
        
        # 4. imprimir detalhes de cada elemento
        for i, elem in enumerate(score_elements[:10]):  # primeiros 10 apenas
            print(f"\n--- elemento {i+1} ---")
            
            # classe
            class_name = elem.get('class', '')
            print(f"   class: {class_name}")
            
            # texto
            text = elem.text
            print(f"   text: '{text}'")
            
            # texto com strip
            if text:
                stripped = text.strip()
                print(f"   stripped: '{stripped}'")
                print(f"   is digit? {stripped.isdigit()}")
            
            # atributos
            team_id = elem.get('data-livescore-team', '')
            print(f"   team_id: {team_id}")
            
            # html do elemento
            html_content = html.tostring(elem, encoding='unicode')
            print(f"   html: {html_content[:100]}...")
        
        # 5. ver também os map-score spans
        print("\n" + "=" * 40)
        print("🔍 spans dentro de map-score:")
        
        map_score_spans = tree.xpath("//span[@class='map-score']/span")
        print(f"✅ encontrados {len(map_score_spans)} elementos")
        
        for i, span in enumerate(map_score_spans[:10]):
            print(f"\n--- map-score span {i+1} ---")
            print(f"   text: '{span.text}'")
            if span.text:
                stripped = span.text.strip()
                print(f"   stripped: '{stripped}'")
                print(f"   is digit? {stripped.isdigit()}")
            print(f"   class: {span.get('class', '')}")
            print(f"   team: {span.get('data-livescore-team', '')}")
        
        # 6. ver o container do primeiro match ao vivo
        print("\n" + "=" * 40)
        print("🔍 primeiro match container com live='true':")
        
        live_containers = tree.xpath("//div[contains(@class, 'match-wrapper') and @live='true']")
        print(f"✅ encontrados {len(live_containers)} containers")
        
        if live_containers:
            first = live_containers[0]
            print(f"\n📦 primeiro container:")
            
            # pegar times
            teams = first.xpath(".//div[contains(@class, 'match-teamname')]/text()")
            print(f"   times: {[t.strip() for t in teams if t.strip()]}")
            
            # pegar scores dentro deste container específico
            container_scores = first.xpath(".//span[contains(@class, 'current-map-score')]")
            print(f"   scores encontrados: {len(container_scores)}")
            
            for j, score in enumerate(container_scores):
                score_text = score.text
                print(f"      score {j+1}: '{score_text}' -> stripped: '{score_text.strip() if score_text else None}'")
        
    except Exception as e:
        print(f"❌ erro: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("✅ TESTE CONCLUÍDO")
    print("=" * 60)


def test_with_cloudscraper():
    """
    test usando cloudscraper (igual ao seu serviço)
    """
    import cloudscraper
    
    print("\n" + "=" * 60)
    print("🧪 TESTE COM CLOUDSCRAPER")
    print("=" * 60)
    
    scraper = cloudscraper.create_scraper()
    url = "https://www.hltv.org/matches"
    
    try:
        response = scraper.get(url, timeout=10)
        print(f"✅ status: {response.status_code}")
        
        tree = html.fromstring(response.content)
        
        score_elements = tree.xpath("//span[contains(@class, 'current-map-score')]")
        print(f"🔍 elementos encontrados: {len(score_elements)}")
        
        for i, elem in enumerate(score_elements[:5]):
            print(f"   elem {i+1}: text='{elem.text}', class='{elem.get('class', '')}'")
            
    except Exception as e:
        print(f"❌ erro: {e}")


def save_html_for_inspection():
    """
    salva o HTML recebido para inspeção manual
    """
    import cloudscraper
    
    print("\n" + "=" * 60)
    print("💾 SALVANDO HTML PARA INSPEÇÃO")
    print("=" * 60)
    
    scraper = cloudscraper.create_scraper()
    url = "https://www.hltv.org/matches"
    
    try:
        response = scraper.get(url, timeout=10)
        
        filename = "hltv_matches_debug.html"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(response.text)
        
        print(f"✅ HTML salvo em: {filename}")
        print(f"📦 tamanho: {len(response.text)} caracteres")
        
        # mostrar primeiras linhas
        print("\n📄 primeiras 10 linhas:")
        lines = response.text.split('\n')[:10]
        for i, line in enumerate(lines):
            print(f"{i+1}: {line[:100]}...")
            
    except Exception as e:
        print(f"❌ erro: {e}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--save":
            save_html_for_inspection()
        elif sys.argv[1] == "--cloud":
            test_with_cloudscraper()
        else:
            test_live_match_score()
    else:
        # executar todos
        test_live_match_score()
        test_with_cloudscraper()
        save_html_for_inspection()