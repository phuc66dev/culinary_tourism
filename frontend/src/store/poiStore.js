import { create } from 'zustand';

/**
 * Zustand Store quản lý dữ liệu POI, ngôn ngữ hiện tại và trạng thái đồng bộ.
 * Phụ trách: Bảo
 */
export const usePOIStore = create((set) => ({
  pois: [],
  selectedPOI: null,
  activeLang: 'vi',
  datasetVersion: null,
  isLoading: false,

  setActiveLang: (lang) => set({ activeLang: lang }),
  setSelectedPOI: (poi) => set({ selectedPOI: poi }),
  setPOIs: (pois, datasetVersion = null) => set({ pois, datasetVersion }),
}));
