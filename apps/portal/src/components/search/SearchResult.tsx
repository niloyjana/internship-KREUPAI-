'use client';

import { forwardRef } from 'react';
import {
  LayoutDashboard,
  BarChart3,
  Bot,
  CheckSquare,
  Plug,
  Settings,
  CreditCard,
  FileText,
  ArrowRight,
  type LucideIcon,
} from 'lucide-react';
import { cn } from '@/lib/utils';

export type SearchResultCategory = 'Pages' | 'Agents' | 'Tasks' | 'Integrations';

export interface SearchResultItem {
  id: string;
  title: string;
  description: string;
  category: SearchResultCategory;
  route: string;
  icon?: string;
}

interface SearchResultProps {
  item: SearchResultItem;
  isSelected: boolean;
  query: string;
  onClick: () => void;
  onMouseEnter: () => void;
}

const categoryIcons: Record<SearchResultCategory, LucideIcon> = {
  Pages: FileText,
  Agents: Bot,
  Tasks: CheckSquare,
  Integrations: Plug,
};

const pageIconMap: Record<string, LucideIcon> = {
  dashboard: LayoutDashboard,
  analytics: BarChart3,
  performance: BarChart3,
  cost: CreditCard,
  audit: FileText,
  workforce: Bot,
  catalog: Bot,
  tasks: CheckSquare,
  queue: CheckSquare,
  live: CheckSquare,
  history: CheckSquare,
  escalations: CheckSquare,
  integrations: Plug,
  settings: Settings,
  billing: CreditCard,
};

function getIcon(item: SearchResultItem): LucideIcon {
  if (item.category === 'Pages') {
    // Try to match by icon key or route segment
    const iconKey = item.icon || item.route.split('/').filter(Boolean).pop() || '';
    return pageIconMap[iconKey] || categoryIcons[item.category];
  }
  return categoryIcons[item.category];
}

const categoryColors: Record<SearchResultCategory, string> = {
  Pages: 'bg-blue-50 text-blue-700',
  Agents: 'bg-purple-50 text-purple-700',
  Tasks: 'bg-amber-50 text-amber-700',
  Integrations: 'bg-emerald-50 text-emerald-700',
};

/**
 * Highlights matching portions of text in the search result title.
 */
function HighlightedText({ text, query }: { text: string; query: string }) {
  if (!query.trim()) {
    return <span>{text}</span>;
  }

  const escapedQuery = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const splitRegex = new RegExp(`(${escapedQuery})`, 'gi');
  const testRegex = new RegExp(`^${escapedQuery}$`, 'i');
  const parts = text.split(splitRegex);

  return (
    <span>
      {parts.map((part, i) =>
        testRegex.test(part) ? (
          <mark
            key={i}
            className="bg-primary-100 text-primary-800 rounded-sm px-0.5 font-semibold"
          >
            {part}
          </mark>
        ) : (
          <span key={i}>{part}</span>
        ),
      )}
    </span>
  );
}

export const SearchResult = forwardRef<HTMLButtonElement, SearchResultProps>(
  function SearchResult({ item, isSelected, query, onClick, onMouseEnter }, ref) {
    const Icon = getIcon(item);

    return (
      <button
        ref={ref}
        type="button"
        role="option"
        aria-selected={isSelected}
        onClick={onClick}
        onMouseEnter={onMouseEnter}
        className={cn(
          'flex w-full items-center gap-3 px-4 py-3 text-left transition-colors outline-none',
          isSelected
            ? 'bg-primary-50 text-primary-900'
            : 'text-gray-700 hover:bg-gray-50',
        )}
      >
        {/* Icon */}
        <div
          className={cn(
            'flex items-center justify-center w-9 h-9 rounded-lg flex-shrink-0',
            isSelected
              ? 'bg-primary-100 text-primary-600'
              : 'bg-gray-100 text-gray-500',
          )}
        >
          <Icon className="w-[18px] h-[18px]" />
        </div>

        {/* Title + description */}
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium truncate">
            <HighlightedText text={item.title} query={query} />
          </div>
          <div className="text-xs text-gray-500 truncate mt-0.5">
            <HighlightedText text={item.description} query={query} />
          </div>
        </div>

        {/* Category badge */}
        <span
          className={cn(
            'text-[10px] font-semibold px-2 py-0.5 rounded-full flex-shrink-0 uppercase tracking-wider',
            categoryColors[item.category],
          )}
        >
          {item.category}
        </span>

        {/* Arrow indicator for selected */}
        {isSelected && (
          <ArrowRight className="w-4 h-4 text-primary-400 flex-shrink-0" />
        )}
      </button>
    );
  },
);
