import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { User, Bot, ExternalLink, Clock, CheckCircle } from "lucide-react";
import type { ChatMessage as ChatMessageType, Citation } from "../types";

interface Props {
  message: ChatMessageType;
}

export default function ChatMessage({ message }: Props) {
  const isUser = message.role === "user";

  if (message.isLoading) {
    return (
      <div className='flex gap-4 message-animate'>
        <div className='w-10 h-10 rounded-xl bg-saffron-100 flex items-center justify-center flex-shrink-0'>
          <Bot className='w-5 h-5 text-saffron-600' />
        </div>
        <div className='flex-1 bg-white rounded-xl p-4 border border-gray-200 shadow-sm'>
          <div className='flex items-center gap-2'>
            <div className='flex gap-1'>
              <span className='w-2 h-2 bg-saffron-500 rounded-full loading-dot' />
              <span className='w-2 h-2 bg-saffron-500 rounded-full loading-dot' />
              <span className='w-2 h-2 bg-saffron-500 rounded-full loading-dot' />
            </div>
            <span className='text-sm text-gray-500'>
              Analyzing your question...
            </span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      className={`flex gap-4 message-animate ${
        isUser ? "flex-row-reverse" : ""
      }`}
    >
      {/* Avatar */}
      <div
        className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${
          isUser ? "bg-gray-200" : "bg-saffron-100"
        }`}
      >
        {isUser ? (
          <User className='w-5 h-5 text-gray-600' />
        ) : (
          <Bot className='w-5 h-5 text-saffron-600' />
        )}
      </div>

      {/* Message Content */}
      <div className={`flex-1 max-w-[80%] ${isUser ? "text-right" : ""}`}>
        <div
          className={`inline-block rounded-xl p-4 ${
            isUser
              ? "bg-saffron-600 text-white"
              : "bg-white border border-gray-200 shadow-sm"
          }`}
        >
          {isUser ? (
            <p className='text-sm leading-relaxed'>{message.content}</p>
          ) : (
            <div className='markdown-content text-sm'>
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {message.content}
              </ReactMarkdown>
            </div>
          )}
        </div>

        {/* Citations */}
        {!isUser && message.citations && message.citations.length > 0 && (
          <Citations citations={message.citations} />
        )}

        {/* Metadata */}
        {!isUser &&
          (message.processingTimeMs || message.validationAttempts) && (
            <div className='flex items-center gap-4 mt-2 text-xs text-gray-400'>
              {message.processingTimeMs && (
                <div className='flex items-center gap-1'>
                  <Clock className='w-3 h-3' />
                  <span>{(message.processingTimeMs / 1000).toFixed(1)}s</span>
                </div>
              )}
              {message.validationAttempts !== undefined &&
                message.validationAttempts > 0 && (
                  <div className='flex items-center gap-1'>
                    <CheckCircle className='w-3 h-3' />
                    <span>
                      Verified ({message.validationAttempts} check
                      {message.validationAttempts > 1 ? "s" : ""})
                    </span>
                  </div>
                )}
            </div>
          )}
      </div>
    </div>
  );
}

interface CitationsProps {
  citations: Citation[];
}

function Citations({ citations }: CitationsProps) {
  return (
    <div className='mt-3 p-3 bg-gray-50 rounded-lg border border-gray-200'>
      <h4 className='text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2'>
        Legal Citations ({citations.length})
      </h4>
      <div className='space-y-2'>
        {citations.map((citation, idx) => {
          const actName = citation.act || citation.law || "Unknown Act";
          return (
            <div
              key={idx}
              className='flex items-start gap-2 p-2 bg-white rounded-lg border border-gray-100 hover:border-saffron-200 transition-colors'
            >
              <span className='citation-badge flex-shrink-0'>{idx + 1}</span>
              <div className='flex-1 min-w-0'>
                <div className='flex items-center gap-2 flex-wrap'>
                  <span className='text-sm font-medium text-gray-900'>
                    {actName}, Section {citation.section}
                  </span>
                  {citation.verified && (
                    <span className='inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800'>
                      <CheckCircle className='w-3 h-3 mr-0.5' />
                      Verified
                    </span>
                  )}
                </div>
                {citation.title && (
                  <p className='text-xs text-gray-600 mt-0.5'>
                    {citation.title}
                  </p>
                )}
                {citation.context && (
                  <p className='text-xs text-gray-500 mt-1 line-clamp-2'>
                    {citation.context}
                  </p>
                )}
                {/* Official URL Link */}
                {citation.url && (
                  <a
                    href={citation.url}
                    target='_blank'
                    rel='noopener noreferrer'
                    className='inline-flex items-center gap-1 mt-2 text-xs text-saffron-600 hover:text-saffron-700 hover:underline'
                  >
                    <ExternalLink className='w-3 h-3' />
                    View Official Source
                  </a>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
