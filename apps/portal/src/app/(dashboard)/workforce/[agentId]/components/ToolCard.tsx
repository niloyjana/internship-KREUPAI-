'use client';

import { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import { toolCategoryColors } from '../constants';
import type { ToolDefinition } from '@/lib/data/agent-tools';

export function ToolCard({ tool }: { tool: ToolDefinition }) {
  const [expanded, setExpanded] = useState(false);
  const catColor = toolCategoryColors[tool.category] || {
    bg: 'bg-gray-100',
    text: 'text-gray-600',
  };

  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4 hover:border-gray-200 transition-colors">
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2 mb-1">
            <h4 className="text-sm font-semibold text-gray-900">{tool.name}</h4>
            <span
              className={cn(
                'px-2 py-0.5 rounded-full text-[10px] font-medium uppercase',
                catColor.bg,
                catColor.text,
              )}
            >
              {tool.category}
            </span>
          </div>
          <p className="text-xs text-gray-500 leading-relaxed">{tool.description}</p>
        </div>
        <span
          className={cn(
            'flex-shrink-0 px-2 py-0.5 rounded-full text-[10px] font-medium',
            tool.implemented ? 'bg-green-50 text-green-700' : 'bg-gray-100 text-gray-500',
          )}
        >
          {tool.implemented ? 'Implemented' : 'Planned'}
        </span>
      </div>

      {/* Parameters toggle */}
      {tool.params.length > 0 && (
        <div className="mt-3">
          <button
            onClick={() => setExpanded(!expanded)}
            className="inline-flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700 transition-colors"
          >
            {expanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
            {tool.params.length} parameter{tool.params.length !== 1 ? 's' : ''}
          </button>
          {expanded && (
            <div className="mt-2 overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-gray-100">
                    <th className="text-left py-1.5 pr-3 font-medium text-gray-500">Name</th>
                    <th className="text-left py-1.5 pr-3 font-medium text-gray-500">Type</th>
                    <th className="text-left py-1.5 pr-3 font-medium text-gray-500">Required</th>
                    <th className="text-left py-1.5 font-medium text-gray-500">Description</th>
                  </tr>
                </thead>
                <tbody>
                  {tool.params.map((p) => (
                    <tr key={p.name} className="border-b border-gray-50">
                      <td className="py-1.5 pr-3 font-mono text-gray-700">{p.name}</td>
                      <td className="py-1.5 pr-3 text-gray-500">{p.type}</td>
                      <td className="py-1.5 pr-3">
                        {p.required ? (
                          <span className="text-red-500 font-medium">Yes</span>
                        ) : (
                          <span className="text-gray-400">No</span>
                        )}
                      </td>
                      <td className="py-1.5 text-gray-500">{p.description}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Source path */}
      <p className="mt-2 text-[10px] text-gray-400 font-mono truncate">{tool.source}</p>
    </div>
  );
}
