import React, { useState, useEffect, useRef } from 'react';
import type { Message, UserSettings } from './types';
import { getFoodRecommendation } from './services/geminiService';
import ChatMessage from './components/ChatMessage';
import ChatInput from './components/ChatInput';
import SettingsPanel from './components/SettingsPanel';

// Debounce hook to delay geocoding until the user stops typing
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);
    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);
  return debouncedValue;
}

const App: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [settings, setSettings] = useState<UserSettings>({
    location: 'Quận 1, TP.HCM',
    food_types: 'Cà phê, không gian yên tĩnh',
    price_range: 'Tầm trung',
    distance_km: 5,
    coordinates: undefined,
  });
  const [selectedPlaceId, setSelectedPlaceId] = useState<string | null>(null);

  const debouncedLocation = useDebounce(settings.location, 1000);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setMessages([
      {
        id: 'initial-ai-message',
        text: 'Chào bạn! Bạn muốn tìm một quán cà phê ưng ý ở Việt Nam hôm nay? ☕ Để có gợi ý tốt nhất, hãy cho phép mình truy cập vị trí của bạn nhé!',
        sender: 'ai',
      },
    ]);

    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          setSettings((prev) => ({
            ...prev,
            location: 'Vị trí hiện tại của bạn',
            coordinates: {
              lat: position.coords.latitude,
              lng: position.coords.longitude,
            },
          }));
        },
        (error) => {
          console.error("Error getting location:", error.message);
        }
      );
    }
  }, []);

  // Effect to automatically geocode the user's typed address using OpenStreetMap Nominatim
  useEffect(() => {
    if (!debouncedLocation || debouncedLocation.trim() === '' || debouncedLocation.startsWith('Vị trí hiện tại của bạn')) {
      if (debouncedLocation.trim() === '') {
        setSettings(prev => ({ ...prev, coordinates: undefined }));
      }
      return;
    }

    const geocodeAddress = async () => {
        const VIETNAM_VIEWBOX = '102.14,23.39,109.46,8.18';

        const searchNominatim = async (query: string) => {
            try {
                const url = `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(query)}&format=json&countrycodes=vn&limit=1&viewbox=${VIETNAM_VIEWBOX}&bounded=1`;
                const response = await fetch(url, {
                    headers: { 'User-Agent': 'VietnamFoodieAssistant/1.0 (https://aistudio.google.com)' }
                });
                if (!response.ok) {
                    console.warn(`Nominatim API request failed for query: "${query}" with status: ${response.status}`);
                    return null;
                }
                const data = await response.json();
                return (data && data.length > 0) ? data[0] : null;
            } catch (error) {
                console.error(`Error during geocoding for query: "${query}"`, error);
                return null;
            }
        };

        const location = debouncedLocation;

        const normalizeVietnameseAddress = (text: string): string => {
            const expansions: { [key: string]: string } = {
                // University abbreviations
                'đh khtn': 'Đại học Khoa học Tự nhiên',
                'dh khtn': 'Đại học Khoa học Tự nhiên',
                'đh bk': 'Đại học Bách Khoa',
                'dh bk': 'Đại học Bách Khoa',
                'đh spkt': 'Đại học Sư phạm Kỹ thuật',
                'dh spkt': 'Đại học Sư phạm Kỹ thuật',
            };
        
            let result = text.toLowerCase();
            
            // Expand university names first
            for (const [abbr, expansion] of Object.entries(expansions)) {
                const regex = new RegExp(`\\b${abbr}\\b`, 'gi');
                result = result.replace(regex, expansion);
            }
        
            // Translate common address terms to improve geocoding
            // e.g., "quận 5" -> "District 5"
            result = result.replace(/\bquận\s+(\d+)\b/gi, 'District $1');
            result = result.replace(/\bq\.\s*(\d+)\b/gi, 'District $1');
            result = result.replace(/\bphường\s+(\d+)\b/gi, 'Ward $1');
            result = result.replace(/\bp\.\s*(\d+)\b/gi, 'Ward $1');

            return result;
        };

        const locationWithoutNumber = location.replace(/^\d+[/\w-]*\s/, '').trim();
        const normalizedLocation = normalizeVietnameseAddress(location);
        
        const queries = new Set<string>();
        const addQuery = (q: string) => q.trim() && queries.add(q.trim());
        
        // Level 1: Normalized/Translated queries - highest chance of success.
        if (normalizedLocation !== location.toLowerCase()) {
            addQuery(normalizedLocation);
            addQuery(`${normalizedLocation}, Ho Chi Minh City, Vietnam`);
        }

        // Level 2: Original user input.
        addQuery(location);
        if (locationWithoutNumber && locationWithoutNumber !== location) {
            addQuery(locationWithoutNumber);
        }

        // Level 3: Add city context for potentially ambiguous queries.
        if (!/hcm|hồ chí minh|tp\.hcm/i.test(location)) {
            addQuery(`${location}, Ho Chi Minh City, Vietnam`);
            if (locationWithoutNumber && locationWithoutNumber !== location) {
               addQuery(`${locationWithoutNumber}, Ho Chi Minh City, Vietnam`);
            }
        }
        
        const uniqueQueries = Array.from(queries);
        
        let result = null;
        for (const query of uniqueQueries) {
            result = await searchNominatim(query);
            if (result) {
                console.log(`Nominatim search successful for query: "${query}"`);
                break; // Found a result, stop searching
            }
        }

        if (result) {
            const { lat, lon } = result;
            console.log(`Geocode successful for "${debouncedLocation}". Found: ${result.display_name} [${lat}, ${lon}]`);
            setSettings(prev => ({
                ...prev,
                coordinates: { lat: parseFloat(lat), lng: parseFloat(lon) }
            }));
        } else {
            console.error(`Geocode was not successful for "${debouncedLocation}". No results found after trying all queries.`);
            setSettings(prev => ({ ...prev, coordinates: undefined }));
        }
    };

    geocodeAddress();
  }, [debouncedLocation]);


  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);
  
  const handleSelectPlace = (placeId: string) => {
    setSelectedPlaceId(placeId);
  };

  const handleSendMessage = async (userMessage: string) => {
    const newUserMessage: Message = {
      id: `user-${Date.now()}`,
      text: userMessage,
      sender: 'user',
    };
    setMessages((prev) => [...prev, newUserMessage]);
    setIsLoading(true);
    setSelectedPlaceId(null);

    const chatHistory = messages
      .filter(msg => msg.id !== 'initial-ai-message')
      .map(msg => ({
        role: msg.sender === 'user' ? 'user' as const : 'model' as const,
        parts: [{ text: msg.text }]
    }));

    const { text, places } = await getFoodRecommendation(userMessage, settings, chatHistory);
    
    const newAiMessage: Message = {
      id: `ai-${Date.now()}`,
      text: text,
      sender: 'ai',
      places: places,
    };
    setMessages((prev) => [...prev, newAiMessage]);
    setIsLoading(false);
  };

  return (
    <div className="flex flex-col md:flex-row h-screen font-sans">
      <SettingsPanel settings={settings} onSettingsChange={setSettings} />
      <div className="flex flex-col flex-1 bg-orange-50">
        <div className="flex-1 p-6 overflow-y-auto">
          {messages.map((msg) => (
            <ChatMessage 
              key={msg.id} 
              message={msg} 
              onSelectPlace={handleSelectPlace}
              selectedPlaceId={selectedPlaceId}
              userLocation={settings.location}
              userCoordinates={settings.coordinates}
            />
          ))}
          {isLoading && (
            <div className="flex items-start gap-4 my-4">
              <div className="flex-shrink-0 w-10 h-10 rounded-full bg-orange-200 flex items-center justify-center animate-pulse"></div>
              <div className="max-w-xl p-4 rounded-2xl shadow-md bg-white rounded-bl-none">
                <div className="flex items-center space-x-2">
                    <div className="w-2 h-2 rounded-full bg-orange-300 animate-bounce [animation-delay:-0.3s]"></div>
	                <div className="w-2 h-2 rounded-full bg-orange-300 animate-bounce [animation-delay:-0.15s]"></div>
	                <div className="w-2 h-2 rounded-full bg-orange-300 animate-bounce"></div>
                </div>
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>
        <ChatInput onSendMessage={handleSendMessage} isLoading={isLoading} />
      </div>
    </div>
  );
};

export default App;