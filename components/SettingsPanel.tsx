
import React from 'react';
import type { UserSettings } from '../types';

interface SettingsPanelProps {
  settings: UserSettings;
  onSettingsChange: (newSettings: UserSettings) => void;
}

const SettingsPanel: React.FC<SettingsPanelProps> = ({ settings, onSettingsChange }) => {
  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    onSettingsChange({
      ...settings,
      [name]: name === 'distance_km' ? Number(value) : value,
    });
  };

  return (
    <div className="w-full md:w-1/3 lg:w-1/4 bg-white p-6 border-r border-gray-200 shadow-lg md:h-screen overflow-y-auto">
      <h2 className="text-2xl font-bold text-orange-600 mb-2">Xin chào! 🇻🇳</h2>
      <p className="text-gray-600 mb-6">Mình là trợ lý ẩm thực. Hãy cho mình biết sở thích của bạn nhé!</p>
      
      <div className="space-y-6">
        <div>
          <label htmlFor="location" className="block text-sm font-medium text-gray-700 mb-1">
            📍 Vị trí của bạn
          </label>
          <input
            type="text"
            id="location"
            name="location"
            value={settings.location}
            onChange={handleChange}
            placeholder="ví dụ: Quận 1, TP.HCM"
            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-orange-500 focus:border-orange-500"
          />
        </div>

        <div>
          <label htmlFor="food_types" className="block text-sm font-medium text-gray-700 mb-1">
            🍜 Món ăn ưa thích
          </label>
          <input
            type="text"
            id="food_types"
            name="food_types"
            value={settings.food_types}
            onChange={handleChange}
            placeholder="ví dụ: Phở, bún chả, đồ nướng"
            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-orange-500 focus:border-orange-500"
          />
        </div>

        <div>
          <label htmlFor="price_range" className="block text-sm font-medium text-gray-700 mb-1">
            💰 Mức giá
          </label>
          <select
            id="price_range"
            name="price_range"
            value={settings.price_range}
            onChange={handleChange}
            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-orange-500 focus:border-orange-500 bg-white"
          >
            <option value="Bình dân">Bình dân</option>
            <option value="Tầm trung">Tầm trung</option>
            <option value="Cao cấp">Cao cấp</option>
          </select>
        </div>

        <div>
          <label htmlFor="distance_km" className="block text-sm font-medium text-gray-700 mb-1">
            🚗 Khoảng cách tối đa: {settings.distance_km} km
          </label>
          <input
            type="range"
            id="distance_km"
            name="distance_km"
            min="1"
            max="20"
            value={settings.distance_km}
            onChange={handleChange}
            className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-orange-500"
          />
        </div>
      </div>
    </div>
  );
};

export default SettingsPanel;
