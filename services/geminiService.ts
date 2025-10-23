import { GoogleGenAI, Type } from "@google/genai";
import type { UserSettings, Place } from '../types';

const getSystemInstruction = (settings: UserSettings): string => `
You are a developer assistant helping improve a Vietnamese restaurant & café recommendation chatbot. Your task is to provide high-quality, structured data.

Respond with a single structured JSON object containing two keys: "summary" and "places". Do not include any text outside of this JSON object.

1.  **"summary" key (The Chat Message):**
    *   This should be a friendly, human-readable list summarizing the recommended cafés in Vietnamese.
    *   Start with an intro sentence, e.g., "Dưới đây là vài quán cà phê phù hợp với yêu cầu của bạn:".
    *   List each place using a numbered emoji format (1️⃣, 2️⃣, 3️⃣...).
    *   **CRITICAL:** Wrap the name of each café in double asterisks (e.g., "**The Coffee House**"). This makes it clickable in the UI.
    *   After the name, include a short, single-line summary of its main highlight.
    *   Example "summary" format:
        "Dưới đây là vài quán cà phê phù hợp với yêu cầu của bạn:\\n1️⃣ **The Coffee House** — Không gian yên tĩnh, nước ngon, nhân viên thân thiện.\\n2️⃣ **Oromia Coffee** — View xanh mát, decor sang trọng, nhiều ổ điện."

2.  **"places" key (The Map Data):**
    *   This should be a JSON array of 5-10 recommended café objects.
    *   Each object must include the following fields:
        - name: Tên của quán.
        - address: Địa chỉ đầy đủ.
        - latitude, longitude: Coordinates must be accurate and within the user's requested area in Vietnam.
        - rating: A number between 4.0 and 5.0.
        - review_count: An estimated number of reviews.
        - reason: A short string with 2-3 bullet points (using "- " and "\\n") explaining in Vietnamese why it’s recommended (e.g., "- Không gian yên tĩnh, phù hợp làm việc.\\n- Đồ uống ngon, nhân viên thân thiện.").
        - images: An array of 1-3 REAL, publicly accessible image URLs that will work in an <img src=""> tag. Use high-quality, generic coffee shop photos from sites like unsplash.com or pexels.com if a specific image is not available. DO NOT invent fake URLs.
        - source: "Google Maps" or "OpenStreetMap".
        - confidence: A float between 0.0 and 1.0.

Rules:
- Results must match the user’s preferences (style, budget, distance).
- Prefer highly rated or popular places.
- **IMAGE CRITICAL**: Ensure all URLs in the 'images' array are valid and publicly accessible. For example: "https://images.unsplash.com/photo-1541167760496-1628856ab772".
- **JSON CRITICAL**: Ensure any double quotes (") inside string values are properly escaped with a backslash (\\").

Example of a single "place" object:
{
  "name": "The Coffee House",
  "address": "196 Trần Hưng Đạo, Quận 5, TP.HCM",
  "latitude": 10.752312,
  "longitude": 106.663801,
  "rating": 4.5,
  "review_count": 320,
  "reason": "- Không gian yên tĩnh, phù hợp làm việc.\\n- Đồ uống ngon, nhân viên thân thiện.",
  "images": [
    "https://images.unsplash.com/photo-1541167760496-1628856ab772",
    "https://images.unsplash.com/photo-1509042239860-f550ce710b93"
  ],
  "source": "Google Maps",
  "confidence": 0.95
}

🗺️ User's context:
- User location text: ${settings.location}
- User's coordinates: ${settings.coordinates ? `${settings.coordinates.lat}, ${settings.coordinates.lng}`: 'Not available'}
- Preferred styles/types: ${settings.food_types}
- Price range: ${settings.price_range}
- Max distance: ${settings.distance_km} km
`;


export interface RecommendationResponse {
    text: string;
    places: Place[];
}

export const getFoodRecommendation = async (
  userMessage: string,
  settings: UserSettings,
  chatHistory: { role: 'user' | 'model'; parts: { text: string }[] }[]
): Promise<RecommendationResponse> => {
  try {
    if (!process.env.API_KEY) {
      throw new Error("API key not found. Please set the API_KEY environment variable.");
    }
    const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });
    
    const model = 'gemini-2.5-flash';

    const placeSchema = {
        type: Type.OBJECT,
        properties: {
          name: { type: Type.STRING, description: 'Tên của quán cà phê.' },
          address: { type: Type.STRING, description: 'Địa chỉ đầy đủ, bao gồm số nhà, đường, quận, và thành phố.' },
          latitude: { type: Type.NUMBER, description: 'Vĩ độ địa lý.' },
          longitude: { type: Type.NUMBER, description: 'Kinh độ địa lý.' },
          rating: { type: Type.NUMBER, description: 'Điểm đánh giá trung bình, từ 0 đến 5.' },
          review_count: { type: Type.NUMBER, description: 'Số lượng đánh giá.' },
          price_range: { type: Type.STRING, description: 'Khoảng giá, ví dụ: "30,000đ - 70,000đ".' },
          opening_hours: { type: Type.STRING, description: 'Giờ mở cửa, ví dụ: "07:00 - 22:00".' },
          reason: { type: Type.STRING, description: 'Lý do đề xuất, định dạng gạch đầu dòng với \\n.' },
          popular_reviews: { type: Type.ARRAY, items: { type: Type.STRING }, description: 'Một hoặc hai đánh giá tiêu biểu của người dùng.' },
          images: { type: Type.ARRAY, items: { type: Type.STRING }, description: 'Link URL hình ảnh của quán.' },
          source: { type: Type.STRING, description: 'Nguồn dữ liệu, ví dụ: "Google Maps".' },
          confidence: { type: Type.NUMBER, description: 'Độ tin cậy của gợi ý, từ 0.0 đến 1.0.' },
        },
        required: ['name', 'address', 'latitude', 'longitude', 'reason', 'images'],
    };

    const responseSchema = {
      type: Type.OBJECT,
      properties: {
        summary: { type: Type.STRING, description: 'A short, friendly summary of the recommendations in Vietnamese.' },
        places: {
          type: Type.ARRAY,
          description: 'A list of recommended coffee shop objects.',
          items: placeSchema
        }
      },
      required: ['summary', 'places'],
    };

    const response = await ai.models.generateContent({
        model: model,
        contents: [ ...chatHistory, { role: 'user', parts: [{ text: userMessage }] }],
        config: {
            systemInstruction: getSystemInstruction(settings),
            responseMimeType: "application/json",
            responseSchema: responseSchema,
        }
    });
    
    const responseData = JSON.parse(response.text);
    const text = responseData.summary || "Tuyệt vời! Dưới đây là một vài gợi ý quán cà phê phù hợp với bạn. Hãy xem trên bản đồ nhé!";
    const placesData = responseData.places || [];

    const places: Place[] = placesData.map((p: any, index: number) => ({
        id: `${p.name.replace(/\s/g, '-')}-${index}`, // Create a stable ID
        title: p.name,
        address: p.address,
        latitude: p.latitude,
        longitude: p.longitude,
        rating: p.rating,
        review_count: p.review_count,
        price_range: p.price_range,
        opening_hours: p.opening_hours,
        reason: p.reason,
        popular_reviews: p.popular_reviews,
        images: p.images,
        source: p.source,
        confidence: p.confidence,
    }));

    return { text, places };
  } catch (error) {
    console.error("Error fetching recommendation:", error);
    let errorMessage = "Xin lỗi, mình đang gặp chút sự cố. Bạn vui lòng thử lại sau nhé! 😥";
    if (error instanceof SyntaxError) {
        errorMessage = "Xin lỗi, mình gặp sự cố khi xử lý dữ liệu từ AI. Có thể định dạng trả về không đúng. Bạn thử lại nhé."
    }
    const errorResponse = {
        text: errorMessage,
        places: []
    };
    return errorResponse;
  }
};