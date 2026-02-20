import { useState, useRef, useEffect, useCallback, type KeyboardEvent } from 'react';
import { useTickerSearch } from '../../api/search';
import { SearchIcon } from '../../assets/icons/SearchIcon';

interface SearchInputProps {
  onSelect: (symbol: string) => void;
  initialValue?: string;
}

export function SearchInput({ onSelect, initialValue = '' }: SearchInputProps) {
  const [input, setInput] = useState(initialValue);
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [open, setOpen] = useState(false);
  const [highlightIndex, setHighlightIndex] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLUListElement>(null);

  // Sync input when initialValue changes (e.g., navigation)
  useEffect(() => {
    setInput(initialValue);
  }, [initialValue]);

  // Debounce input by 300ms
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQuery(input.trim()), 300);
    return () => clearTimeout(timer);
  }, [input]);

  const { data } = useTickerSearch(debouncedQuery);
  const results = data?.results ?? [];

  // Show dropdown when we have results and input is focused
  useEffect(() => {
    if (results.length > 0 && input.length > 0) {
      setOpen(true);
    }
  }, [results, input]);

  const select = useCallback(
    (symbol: string) => {
      setInput(symbol);
      setOpen(false);
      setHighlightIndex(-1);
      onSelect(symbol);
    },
    [onSelect]
  );

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (!open || results.length === 0) {
      if (e.key === 'Enter' && input.trim()) {
        select(input.trim().toUpperCase());
      }
      return;
    }

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setHighlightIndex((prev) => Math.min(prev + 1, results.length - 1));
        break;
      case 'ArrowUp':
        e.preventDefault();
        setHighlightIndex((prev) => Math.max(prev - 1, 0));
        break;
      case 'Enter':
        e.preventDefault();
        if (highlightIndex >= 0 && highlightIndex < results.length) {
          select(results[highlightIndex].symbol);
        } else if (input.trim()) {
          select(input.trim().toUpperCase());
        }
        break;
      case 'Escape':
        setOpen(false);
        setHighlightIndex(-1);
        break;
    }
  };

  // Scroll highlighted item into view
  useEffect(() => {
    if (highlightIndex >= 0 && listRef.current) {
      const item = listRef.current.children[highlightIndex] as HTMLElement;
      item?.scrollIntoView({ block: 'nearest' });
    }
  }, [highlightIndex]);

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      const target = e.target as Node;
      if (!inputRef.current?.parentElement?.contains(target)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  return (
    <div className="relative w-full max-w-md">
      <div className="relative">
        <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => {
            setInput(e.target.value);
            setHighlightIndex(-1);
          }}
          onFocus={() => {
            if (results.length > 0 && input.length > 0) setOpen(true);
          }}
          onKeyDown={handleKeyDown}
          placeholder="Search stocks (e.g. AAPL, Tesla)..."
          className="w-full pl-9 pr-4 py-2.5 bg-background border border-border rounded-lg text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary transition-colors"
          role="combobox"
          aria-expanded={open}
          aria-controls="search-listbox"
          aria-autocomplete="list"
          aria-activedescendant={
            highlightIndex >= 0 ? `search-option-${highlightIndex}` : undefined
          }
          autoComplete="off"
        />
      </div>

      {open && results.length > 0 && (
        <ul
          ref={listRef}
          id="search-listbox"
          role="listbox"
          className="absolute z-20 mt-1 w-full max-h-72 overflow-auto bg-card border border-border rounded-lg shadow-lg"
        >
          {results.map((r, i) => (
            <li
              key={r.symbol}
              id={`search-option-${i}`}
              role="option"
              aria-selected={highlightIndex === i}
              onMouseDown={() => select(r.symbol)}
              onMouseEnter={() => setHighlightIndex(i)}
              className={`flex items-center justify-between px-3 py-2.5 cursor-pointer text-sm transition-colors ${
                highlightIndex === i
                  ? 'bg-primary/10 text-foreground'
                  : 'text-foreground hover:bg-muted'
              }`}
            >
              <div className="flex items-center gap-3 min-w-0">
                <span className="font-semibold shrink-0">{r.symbol}</span>
                <span className="text-muted-foreground truncate">{r.name}</span>
              </div>
              {r.exchange && (
                <span className="text-xs text-muted-foreground shrink-0 ml-2">
                  {r.exchange}
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
