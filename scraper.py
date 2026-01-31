"""
Blood Bank Agent - News Scraper
Scrapes blood center websites for shortage announcements and status updates
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import re
import json
from dataclasses import dataclass


@dataclass
class ShortageAlert:
    """Represents a detected shortage alert"""
    source: str
    region_id: Optional[int]
    severity: str  # critical, severe, moderate, low
    blood_types_affected: List[str]
    headline: str
    date_detected: datetime
    url: str
    confidence: float  # 0-1 confidence in detection


class BloodCenterScraper:
    """
    Scrapes major blood center websites for shortage information
    """
    
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (compatible; BloodBankResearchBot/1.0)"
        }
        
        # Keywords indicating shortage severity
        self.severity_keywords = {
            "critical": ["critical", "crisis", "emergency", "urgent", "dire", "severe shortage"],
            "severe": ["severe", "serious", "significant shortage", "plummeted", "drastically"],
            "moderate": ["shortage", "low supply", "need donors", "decreased"],
            "low": ["needed", "encouraged to donate", "help needed"]
        }
        
        # Blood type patterns
        self.blood_type_pattern = re.compile(
            r'\b(O[\s-]?(positive|negative|\+|-))|'
            r'(A[\s-]?(positive|negative|\+|-))|'
            r'(B[\s-]?(positive|negative|\+|-))|'
            r'(AB[\s-]?(positive|negative|\+|-))|'
            r'(type\s+O|type\s+A|type\s+B|type\s+AB)\b',
            re.IGNORECASE
        )
        
        # Region keywords for geographic detection
        self.region_keywords = {
            1: ["new england", "boston", "connecticut", "maine", "massachusetts", "rhode island", "vermont", "new hampshire"],
            2: ["new york", "new jersey", "nyc", "manhattan", "brooklyn"],
            3: ["philadelphia", "baltimore", "maryland", "pennsylvania", "virginia", "delaware", "dc", "washington dc"],
            4: ["florida", "georgia", "atlanta", "miami", "southeast", "carolina", "tennessee", "alabama", "kentucky"],
            5: ["chicago", "illinois", "michigan", "ohio", "wisconsin", "minnesota", "midwest", "indiana"],
            6: ["texas", "houston", "dallas", "louisiana", "new orleans", "oklahoma", "arkansas"],
            7: ["kansas", "missouri", "iowa", "nebraska", "kansas city", "omaha"],
            8: ["colorado", "denver", "utah", "montana", "wyoming", "mountain"],
            9: ["california", "los angeles", "san francisco", "arizona", "phoenix", "nevada", "las vegas", "hawaii"],
            10: ["seattle", "washington state", "oregon", "portland", "pacific northwest", "idaho", "alaska"]
        }
        
        # Target URLs and their associated regions
        self.sources = {
            "red_cross_national": {
                "url": "https://www.redcross.org/about-us/news-and-events/press-release.html",
                "region": None,  # National
                "parser": self._parse_red_cross
            },
            "ny_blood_center": {
                "url": "https://www.nybc.org/news/",
                "region": 2,
                "parser": self._parse_generic_news
            },
            "oneblood": {
                "url": "https://www.oneblood.org/about-us/newsroom/",
                "region": 4,
                "parser": self._parse_generic_news
            },
            "vitalant": {
                "url": "https://www.vitalant.org/newsroom",
                "region": None,  # Multiple regions
                "parser": self._parse_generic_news
            },
            "versiti": {
                "url": "https://www.versiti.org/news",
                "region": 5,
                "parser": self._parse_generic_news
            }
        }
    
    def scrape_all_sources(self) -> List[ShortageAlert]:
        """Scrape all configured sources and return alerts"""
        all_alerts = []
        
        for source_name, config in self.sources.items():
            try:
                print(f"Scraping {source_name}...")
                alerts = self._scrape_source(source_name, config)
                all_alerts.extend(alerts)
            except Exception as e:
                print(f"Error scraping {source_name}: {e}")
        
        return all_alerts
    
    def _scrape_source(self, source_name: str, config: Dict) -> List[ShortageAlert]:
        """Scrape a single source"""
        try:
            response = requests.get(config["url"], headers=self.headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            parser = config.get("parser", self._parse_generic_news)
            
            return parser(soup, source_name, config)
            
        except requests.RequestException as e:
            print(f"Request failed for {source_name}: {e}")
            return []
    
    def _parse_red_cross(self, soup: BeautifulSoup, source: str, config: Dict) -> List[ShortageAlert]:
        """Parse Red Cross press releases"""
        alerts = []
        
        # Look for news items
        news_items = soup.find_all(['article', 'div'], class_=re.compile(r'news|press|article|item'))
        
        for item in news_items[:10]:  # Check first 10 items
            text = item.get_text().lower()
            headline_elem = item.find(['h2', 'h3', 'h4', 'a'])
            headline = headline_elem.get_text().strip() if headline_elem else ""
            
            # Check for shortage keywords
            severity = self._detect_severity(text)
            if severity:
                blood_types = self._extract_blood_types(text)
                region = self._detect_region(text) or config.get("region")
                
                alerts.append(ShortageAlert(
                    source=source,
                    region_id=region,
                    severity=severity,
                    blood_types_affected=blood_types,
                    headline=headline[:200],
                    date_detected=datetime.now(),
                    url=config["url"],
                    confidence=self._calculate_confidence(text, severity)
                ))
        
        return alerts
    
    def _parse_generic_news(self, soup: BeautifulSoup, source: str, config: Dict) -> List[ShortageAlert]:
        """Generic news parser for most blood center sites"""
        alerts = []
        
        # Find all text-containing elements
        text_elements = soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'article', 'div'])
        
        full_text = " ".join([elem.get_text() for elem in text_elements]).lower()
        
        # Check for shortage indicators
        severity = self._detect_severity(full_text)
        if severity:
            blood_types = self._extract_blood_types(full_text)
            region = self._detect_region(full_text) or config.get("region")
            
            # Try to find a headline
            headline_elem = soup.find(['h1', 'h2'])
            headline = headline_elem.get_text().strip() if headline_elem else f"Blood supply alert from {source}"
            
            alerts.append(ShortageAlert(
                source=source,
                region_id=region,
                severity=severity,
                blood_types_affected=blood_types,
                headline=headline[:200],
                date_detected=datetime.now(),
                url=config["url"],
                confidence=self._calculate_confidence(full_text, severity)
            ))
        
        return alerts
    
    def _detect_severity(self, text: str) -> Optional[str]:
        """Detect shortage severity from text"""
        text = text.lower()
        
        for severity, keywords in self.severity_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    return severity
        
        return None
    
    def _extract_blood_types(self, text: str) -> List[str]:
        """Extract mentioned blood types from text"""
        matches = self.blood_type_pattern.findall(text)
        
        blood_types = set()
        for match in matches:
            # Flatten tuple and clean
            for part in match:
                if part:
                    cleaned = part.upper().replace(" ", "").replace("-", "")
                    # Normalize
                    cleaned = cleaned.replace("POSITIVE", "+").replace("NEGATIVE", "-")
                    if cleaned and len(cleaned) <= 4:
                        blood_types.add(cleaned)
        
        # If no specific types found but shortage mentioned, assume O types (most common need)
        if not blood_types and ("shortage" in text or "need" in text):
            blood_types = {"O+", "O-"}
        
        return list(blood_types)
    
    def _detect_region(self, text: str) -> Optional[int]:
        """Detect HHS region from geographic keywords in text"""
        text = text.lower()
        
        region_scores = {r: 0 for r in range(1, 11)}
        
        for region_id, keywords in self.region_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    region_scores[region_id] += 1
        
        # Return region with highest score if any matches
        max_score = max(region_scores.values())
        if max_score > 0:
            return max(region_scores, key=region_scores.get)
        
        return None
    
    def _calculate_confidence(self, text: str, severity: str) -> float:
        """Calculate confidence score for detection"""
        confidence = 0.5  # Base confidence
        
        # More severe keywords = higher confidence
        if severity == "critical":
            confidence += 0.3
        elif severity == "severe":
            confidence += 0.2
        elif severity == "moderate":
            confidence += 0.1
        
        # Multiple shortage keywords = higher confidence
        shortage_count = sum(1 for kw in ["shortage", "low", "need", "crisis", "emergency"] if kw in text.lower())
        confidence += min(0.2, shortage_count * 0.05)
        
        # Recent date mentioned = higher confidence
        if any(word in text.lower() for word in ["today", "this week", "january", "february"]):
            confidence += 0.1
        
        return min(1.0, confidence)


class SimulatedAlertGenerator:
    """
    Generates realistic simulated alerts when scraping fails
    or for demo purposes
    """
    
    def __init__(self):
        import random
        self.random = random
    
    def generate_regional_status(self) -> Dict[int, Dict]:
        """Generate simulated status for all regions"""
        status = {}
        
        for region_id in range(1, 11):
            # Base probability of shortage
            shortage_prob = 0.25  # 25% chance of some shortage
            
            # Seasonal adjustment (winter = higher shortage risk)
            month = datetime.now().month
            if month in [12, 1, 2]:
                shortage_prob += 0.2
            elif month in [6, 7, 8]:
                shortage_prob += 0.15
            
            has_shortage = self.random.random() < shortage_prob
            
            if has_shortage:
                severity = self.random.choices(
                    ["critical", "severe", "moderate", "low"],
                    weights=[0.1, 0.25, 0.4, 0.25]
                )[0]
                
                # Affected blood types (O types most commonly affected)
                all_types = ["O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-"]
                num_affected = self.random.randint(1, 4)
                # Weight towards O types
                weights = [0.3, 0.25, 0.15, 0.1, 0.08, 0.05, 0.04, 0.03]
                affected = self.random.choices(all_types, weights=weights, k=num_affected)
                
                status[region_id] = {
                    "has_shortage": True,
                    "severity": severity,
                    "blood_types_affected": list(set(affected)),
                    "days_of_supply": self._severity_to_days(severity),
                    "simulated": True
                }
            else:
                status[region_id] = {
                    "has_shortage": False,
                    "severity": "adequate",
                    "blood_types_affected": [],
                    "days_of_supply": self.random.uniform(2.5, 4.5),
                    "simulated": True
                }
        
        return status
    
    def _severity_to_days(self, severity: str) -> float:
        """Convert severity to approximate days of supply"""
        mapping = {
            "critical": self.random.uniform(0.3, 0.8),
            "severe": self.random.uniform(0.8, 1.5),
            "moderate": self.random.uniform(1.5, 2.5),
            "low": self.random.uniform(2.0, 3.0),
            "adequate": self.random.uniform(3.0, 5.0)
        }
        return round(mapping.get(severity, 3.0), 2)


def get_shortage_intelligence() -> Dict:
    """
    Main function to gather shortage intelligence from all sources
    Returns combined scraped and simulated data
    """
    scraper = BloodCenterScraper()
    simulator = SimulatedAlertGenerator()
    
    # Try scraping real sources
    print("Attempting to scrape blood center news...")
    scraped_alerts = []
    try:
        scraped_alerts = scraper.scrape_all_sources()
        print(f"Found {len(scraped_alerts)} alerts from scraping")
    except Exception as e:
        print(f"Scraping failed: {e}")
    
    # Generate simulated regional status
    print("Generating regional status simulation...")
    simulated_status = simulator.generate_regional_status()
    
    # Merge scraped alerts into simulated status
    for alert in scraped_alerts:
        if alert.region_id and alert.region_id in simulated_status:
            # Override simulation with real data
            simulated_status[alert.region_id].update({
                "has_shortage": alert.severity in ["critical", "severe", "moderate"],
                "severity": alert.severity,
                "blood_types_affected": alert.blood_types_affected,
                "source": alert.source,
                "headline": alert.headline,
                "confidence": alert.confidence,
                "simulated": False
            })
    
    return {
        "timestamp": datetime.now().isoformat(),
        "scraped_alerts": [
            {
                "source": a.source,
                "region_id": a.region_id,
                "severity": a.severity,
                "blood_types": a.blood_types_affected,
                "headline": a.headline,
                "confidence": a.confidence
            }
            for a in scraped_alerts
        ],
        "regional_status": simulated_status
    }


if __name__ == "__main__":
    # Test scraping
    result = get_shortage_intelligence()
    print(json.dumps(result, indent=2, default=str))
