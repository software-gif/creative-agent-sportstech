"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { supabase } from "./supabase";

type Brand = {
  id: string;
  name: string;
};

type BrandContextType = {
  brandId: string | null;
  setBrandId: (id: string) => void;
  brands: Brand[];
  loading: boolean;
};

const BrandContext = createContext<BrandContextType>({
  brandId: null,
  setBrandId: () => {},
  brands: [],
  loading: true,
});

export function BrandProvider({ children }: { children: React.ReactNode }) {
  const [brandId, setBrandIdState] = useState<string | null>(null);
  const [brands, setBrands] = useState<Brand[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadBrands();
  }, []);

  async function loadBrands() {
    const { data, error } = await supabase
      .from("brands")
      .select("id, name")
      .order("name");

    if (!error && data && data.length > 0) {
      setBrands(data);
      // Restore from localStorage or URL param, or use first brand
      const stored = localStorage.getItem("selectedBrandId");
      const url = new URL(window.location.href);
      const urlBrand = url.searchParams.get("brand");

      const targetId = urlBrand || stored || data[0].id;
      const valid = data.find((b) => b.id === targetId);
      setBrandIdState(valid ? valid.id : data[0].id);
    }
    setLoading(false);
  }

  function setBrandId(id: string) {
    setBrandIdState(id);
    localStorage.setItem("selectedBrandId", id);
    // Update URL param without navigation
    const url = new URL(window.location.href);
    url.searchParams.set("brand", id);
    window.history.replaceState({}, "", url.toString());
  }

  return (
    <BrandContext.Provider value={{ brandId, setBrandId, brands, loading }}>
      {children}
    </BrandContext.Provider>
  );
}

export function useBrand() {
  return useContext(BrandContext);
}
