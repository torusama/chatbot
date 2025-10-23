import React from 'react';
import type { Message } from '../types';
import BotIcon from './icons/BotIcon';
import UserIcon from './icons/UserIcon';
import MapComponent from './MapComponent';

interface ChatMessageProps {
  message: Message;
  onSelectPlace: (placeId: string) => void;
  selectedPlaceId: string | null;
  userLocation: string;
  userCoordinates?: { lat: number, lng: number };
}

const ChatMessage: React.FC<ChatMessageProps> = ({ message, onSelectPlace, selectedPlaceId, userLocation, userCoordinates }) => {
  const isUser = message.sender === 'user';

  const renderText = (text: string) => {
    const parts = text.split(/(\*\*.*?\*\*)/g);
    return parts.map((part, index) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        const placeName = part.slice(2, -2);
        const place = message.places?.find(p => p.title === placeName);
        if (place) {
          const isSelected = selectedPlaceId === place.id;
          return (
            <button
              key={index}
              onClick={() => onSelectPlace(place.id)}
              className={`font-bold hover:underline focus:outline-none transition-all duration-200 ${
                isSelected
                  ? 'text-orange-900 bg-orange-200 px-2 py-1 rounded-md'
                  : 'text-orange-600'
              }`}
              aria-label={`Hiển thị ${placeName} trên bản đồ`}
            >
              {placeName}
            </button>
          );
        }
        return <strong key={index}>{placeName}</strong>;
      }
      return part.split('\n').map((line, lineIndex) => (
          <React.Fragment key={`${index}-${lineIndex}`}>
            {line}
            {lineIndex < part.split('\n').length - 1 && <br />}
          </React.Fragment>
      ));
    });
  };

  return (
    <div className={`flex items-start gap-4 my-4 ${isUser ? 'justify-end' : ''}`}>
      {!isUser && (
        <div className="flex-shrink-0 w-10 h-10 rounded-full bg-orange-200 flex items-center justify-center">
          <BotIcon className="w-6 h-6 text-orange-600" />
        </div>
      )}
      <div
        className={`flex flex-col gap-3 max-w-xl p-4 rounded-2xl shadow-md ${
          isUser
            ? 'bg-orange-500 text-white rounded-br-none'
            : 'bg-white text-gray-800 rounded-bl-none'
        }`}
      >
        <div className="whitespace-pre-wrap">{renderText(message.text)}</div>
        {!isUser && message.places && message.places.length > 0 && (
          <div className="mt-2 -mx-1 -mb-1">
            <MapComponent 
              places={message.places} 
              selectedPlaceId={selectedPlaceId}
              onSelectPlace={onSelectPlace}
              userLocation={userLocation}
              userCoordinates={userCoordinates}
            />
          </div>
        )}
      </div>
       {isUser && (
        <div className="flex-shrink-0 w-10 h-10 rounded-full bg-gray-300 flex items-center justify-center">
          <UserIcon className="w-6 h-6 text-gray-700" />
        </div>
      )}
    </div>
  );
};

export default ChatMessage;