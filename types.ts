export interface Place {
  id: string;
  title: string; // Mapped from 'name'
  address: string;
  latitude: number;
  longitude: number;
  rating?: number;
  review_count?: number;
  price_range?: string;
  opening_hours?: string;
  reason?: string;
  popular_reviews?: string[];
  images?: string[];
  source?: string;
  confidence?: number;
}

export interface Message {
  id: string;
  text: string;
  sender: 'user' | 'ai';
  places?: Place[];
}

export interface UserSettings {
  location: string;
  food_types: string;
  price_range: string;
  distance_km: number;
  coordinates?: { lat: number, lng: number };
}