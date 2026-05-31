"use client";

import React, { useEffect, useRef, useState } from "react";
import { ChevronDown } from "lucide-react";

type DropdownProps = {
  value?: string;
  onValueChange: (v: string) => void;
  placeholder?: string;
  className?: string;
  children?: React.ReactNode;
};

function Item(_: { value: string; children?: React.ReactNode }) {
  // This is a slot element; rendering happens in the parent Dropdown.
  return null;
}

export default function Dropdown({ value, onValueChange, placeholder, className = "", children }: DropdownProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement | null>(null);

  // Extract items from children (expecting <Dropdown.Item value="x">Label</Dropdown.Item>)
  const items = React.Children.toArray(children)
    .filter(React.isValidElement)
    .map((el) => ({ value: (el.props as any).value as string, label: (el.props as any).children }));

  const selected = items.find((i) => i.value === value);

  useEffect(() => {
    function onDoc(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }

    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  return (
    <div ref={ref} className={`relative ${className}`}>
      <button
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => setOpen((s) => !s)}
        className="w-full text-left h-10 px-3 pr-10 rounded-none border border-gray-400 dark:border-slate-600 bg-white dark:bg-slate-900 text-black dark:text-white relative"
      >
        <span className={`block truncate ${selected ? "text-black dark:text-white" : "text-gray-400 dark:text-gray-500"}`}>
          {selected ? selected.label : placeholder ?? "Select..."}
        </span>
        <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-gray-600 dark:text-gray-400 h-4 w-4" />
      </button>

      {open && (
        <ul
          role="listbox"
          className="absolute z-50 mt-[-1px] w-full max-h-60 overflow-auto rounded-none border border-gray-400 dark:border-slate-600 bg-white dark:bg-slate-900 p-0"
        >
          {items.map((it) => (
            <li
              key={it.value}
              role="option"
              aria-selected={it.value === value}
              onClick={() => {
                onValueChange(it.value);
                setOpen(false);
              }}
              className={`px-3 py-2 rounded-none cursor-pointer truncate text-black dark:text-white ${
                it.value === value 
                  ? "bg-[#3399ff] text-white" 
                  : "hover:bg-[#e5f1fb] dark:hover:bg-slate-800 hover:text-black dark:hover:text-white"
              }`}
            >
              {it.label}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

(Dropdown as any).Item = Item;

export const DropdownItem = Item;