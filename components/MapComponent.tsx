import React, { useEffect, useRef, useState } from 'react';
import type { Place } from '../types';

// Declare L for Leaflet on window
declare global {
  interface Window {
    L: any;
  }
}

/**
 * Fix for Leaflet's default icon path issue when using a CDN or bundler.
 */
const fixLeafletIconPaths = () => {
    if (window.L) {
        delete (window.L.Icon.Default.prototype as any)._getIconUrl;
        window.L.Icon.Default.mergeOptions({
            iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
            iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
            shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
        });
    }
};

interface MapComponentProps {
  places: Place[];
  selectedPlaceId: string | null;
  onSelectPlace: (placeId: string) => void;
  userLocation: string;
  userCoordinates?: { lat: number; lng: number };
}

interface MarkerInfo {
    marker: any;
}

const MapComponent: React.FC<MapComponentProps> = ({ places, selectedPlaceId, onSelectPlace, userCoordinates }) => {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstance = useRef<any | null>(null);
  const markersRef = useRef<{ [key: string]: MarkerInfo }>({});
  const [isMapInitialized, setIsMapInitialized] = useState(false);
  
  useEffect(() => {
    fixLeafletIconPaths();
  }, []);

  // Effect to initialize the Leaflet map
  useEffect(() => {
    if (!mapRef.current || mapInstance.current) {
        return;
    }

    const initialCoords: [number, number] = userCoordinates 
        ? [userCoordinates.lat, userCoordinates.lng] 
        : [10.7769, 106.7009]; // Default to HCMC center

    mapInstance.current = window.L.map(mapRef.current).setView(initialCoords, 14);
    setIsMapInitialized(true);

    window.L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(mapInstance.current);

    // Fix for potential rendering race condition by invalidating size after mount.
    const resizeTimeout = setTimeout(() => {
        if (mapInstance.current) {
            mapInstance.current.invalidateSize();
        }
    }, 100);

    return () => {
        clearTimeout(resizeTimeout);
        if (mapInstance.current) {
            mapInstance.current.remove();
            mapInstance.current = null;
        }
    };
  }, []); // Only run once on mount
  
  // Effect to add/update markers using coordinates directly from the places prop
  useEffect(() => {
    if (!isMapInitialized || !mapInstance.current) return;
    
    const map = mapInstance.current;

    // Clear any existing markers before adding new ones
    (Object.values(markersRef.current) as MarkerInfo[]).forEach((info) => info.marker.remove());
    markersRef.current = {};
    
    const addMarkersFromPlaces = () => {
        const markerGroup: any[] = [];
        // Ensure we don't add duplicate markers for the same place title
        const uniquePlaces = Array.from(new Map(places.map(p => [p.title, p])).values());

        for (const place of uniquePlaces) {
            // Use coordinates directly from the place object
            if (place.latitude && place.longitude) {
                const latNum = place.latitude;
                const lonNum = place.longitude;
                console.log(`✅ Marker added for ${place.title} at [${latNum}, ${lonNum}]`);

                const marker = window.L.marker([latNum, lonNum], { title: place.title }).addTo(map);

                const popupContent = `
                    <div class="font-sans max-w-xs -m-2 text-gray-800" style="max-width:220px;">
                        ${place.images && place.images.length > 0 ? `<img src="${place.images[0]}" alt="${place.title}" class="w-full h-24 object-cover rounded-t-lg" />` : ''}
                        <div class="p-2">
                            <strong class="text-base text-orange-700 block leading-tight">${place.title}</strong>
                            <p class="text-xs my-1 text-gray-600">${place.address}</p>
                            <div class="flex items-center justify-between text-xs text-gray-500 mt-2 space-x-2">
                                ${place.rating ? `<span>⭐ <strong>${place.rating}</strong>/5</span>` : ''}
                                ${place.review_count ? `<span>👥 ${place.review_count} reviews</span>` : ''}
                            </div>
                             <div class="flex items-center justify-between text-xs text-gray-500 mt-1 space-x-2">
                                ${place.opening_hours ? `<span>🕒 ${place.opening_hours}</span>` : ''}
                                ${place.price_range ? `<span>💰 ${place.price_range}</span>` : ''}
                            </div>
                            ${place.reason ? `<p class="text-xs mt-2 text-gray-600 italic">"${place.reason}"</p>` : ''}
                        </div>
                         ${(place.source || place.confidence) ? `<div class="p-2 pt-1 mt-1 border-t border-gray-200 text-right text-[10px] text-gray-400">
                           ${place.source ? `Source: ${place.source}`: ''} ${place.confidence ? `(Conf: ${(place.confidence * 100).toFixed(0)}%)` : ''}
                         </div>` : ''}
                    </div>`;

                marker.bindPopup(popupContent);
                markersRef.current[place.id] = { marker };
                markerGroup.push(marker);
                
                marker.on('click', () => onSelectPlace(place.id));
            } else {
                 console.warn(`⚠️ Missing coordinates for "${place.title}"`);
            }
        }
      
        if (markerGroup.length > 0) {
            const group = window.L.featureGroup(markerGroup);
            map.fitBounds(group.getBounds().pad(0.2)); // Zoom to fit all markers
        } else if (userCoordinates) {
            map.setView([userCoordinates.lat, userCoordinates.lng], 14); // Center on user if no markers found
        }
    };

    addMarkersFromPlaces();
  }, [places, onSelectPlace, userCoordinates, isMapInitialized]);

  // Effect to handle selecting a place from the chat text, which zooms and opens the popup
  useEffect(() => {
    if (selectedPlaceId && markersRef.current[selectedPlaceId] && mapInstance.current) {
      const { marker } = markersRef.current[selectedPlaceId];
      const map = mapInstance.current;
      
      map.flyTo(marker.getLatLng(), 16, { animate: true, duration: 1 });
      marker.openPopup();
    }
  }, [selectedPlaceId]); // Only re-run if selection changes
  
  return (
    <div className="w-full">
      <div 
        ref={mapRef} 
        className="w-full h-72 rounded-xl overflow-hidden bg-gray-200 border flex items-center justify-center text-center p-4" 
        aria-label="Map of recommended places"
      >
        {!isMapInitialized && (
            <div className="text-gray-500 animate-pulse">Đang tải bản đồ...</div>
        )}
      </div>
    </div>
  );
};

export default MapComponent;