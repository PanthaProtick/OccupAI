import { useEffect, useRef, useState, type FormEvent } from "react";
import { AlertTriangle, ArrowRight, Bot, Clock3, LoaderCircle, RotateCcw, Send, Sparkles, User } from "lucide-react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { AssistantConversationSummary, AssistantMessage, AssistantQueryResponse, AssistantResult } from "../api/types";

const suggestions = [
  "What are the three quietest rooms right now?",
  "Find free rooms on the Ground and First floors.",
  "Which rooms can fit 20 people?",
  "Suggest an alternative to the busiest room.",
  "Show rooms below 40% occupancy.",
  "Should I go to the Library or Study Room now?",
];

type DisplayMessage = Pick<AssistantMessage,"id"|"role"|"content"|"created_at"> & {
  results?:AssistantResult[]; dataTimestamp?:string; warnings?:string[];
};
const friendlyError = (error:unknown) => error instanceof Error && error.message
  ? error.message : "The Campus Assistant is unavailable right now. Please try again.";
const displayTimestamp = (value:string) => new Intl.DateTimeFormat(undefined, {
  dateStyle:"medium", timeStyle:"short",
}).format(new Date(value));

function restoredMessage(message:AssistantMessage):DisplayMessage {
  const structured = message.structured_results;
  return {...message, results:structured?.results, dataTimestamp:structured?.data_timestamp,
    warnings:structured?.warnings};
}

function ResultCards({results}:{results:AssistantResult[]}) {
  if (!results.length) return <p className="assistant-no-results">I couldn’t find a fresh reading for that request. Try another room name, floor, or block and I’ll check again.</p>;
  return <div className="assistant-results" role="region" aria-label="Recommended rooms">{results.map((room,index)=><article className="assistant-result" key={room.room_id}>
    <span className="assistant-result__rank">{index+1}</span>
    <div><p>{room.building} · {room.floor === 0 ? "Ground Floor" : `Floor ${room.floor}`} · {room.block} Block</p>
      <h3>{room.name}</h3><strong>{room.occupancy_percentage}% occupied</strong>
      <span>{room.occupancy} occupied · approximately {room.available_capacity} of {room.capacity} seats available</span>
      <small>{room.reason}</small></div>
    <Link to={`/rooms/${encodeURIComponent(room.room_id)}`} aria-label={`View room ${room.name}`}>View room <ArrowRight size={15}/></Link>
  </article>)}</div>;
}

export function AssistantPage() {
  const [input,setInput]=useState("");
  const [messages,setMessages]=useState<DisplayMessage[]>([]);
  const [conversations,setConversations]=useState<AssistantConversationSummary[]>([]);
  const [conversationId,setConversationId]=useState<string>();
  const [loadingHistory,setLoadingHistory]=useState(true);
  const [pending,setPending]=useState(false);
  const [error,setError]=useState<string>();
  const [lastQuestion,setLastQuestion]=useState<string>();
  const endRef=useRef<HTMLDivElement>(null);

  useEffect(()=>{
    const controller=new AbortController();
    (async()=>{try{
      const list=await api.getAssistantConversations({signal:controller.signal});
      setConversations(list.items);
      if(list.items[0]){
        const conversation=await api.getAssistantConversation(list.items[0].id,{signal:controller.signal});
        setConversationId(conversation.id); setMessages(conversation.messages.map(restoredMessage));
      }
    }catch(reason){if(!controller.signal.aborted)setError(friendlyError(reason));}
    finally{if(!controller.signal.aborted)setLoadingHistory(false);}})();
    return()=>controller.abort();
  },[]);
  useEffect(()=>{endRef.current?.scrollIntoView?.({block:"nearest"});},[messages,pending]);

  const openConversation=async(id:string)=>{if(pending||id===conversationId)return;setError(undefined);setLoadingHistory(true);
    try{const value=await api.getAssistantConversation(id);setConversationId(id);setMessages(value.messages.map(restoredMessage));}
    catch(reason){setError(friendlyError(reason));}finally{setLoadingHistory(false);}};
  const send=async(question:string)=>{const clean=question.trim();if(!clean||pending)return;
    setPending(true);setError(undefined);setLastQuestion(clean);setInput("");
    const userMessage:DisplayMessage={id:`local-${Date.now()}`,role:"user",content:clean,created_at:new Date().toISOString()};
    setMessages(current=>[...current,userMessage]);
    try{const response:AssistantQueryResponse=await api.queryAssistant({message:clean,...(conversationId?{conversation_id:conversationId}:{})});
      setConversationId(response.conversation_id);
      setMessages(current=>[...current,{id:`assistant-${Date.now()}`,role:"assistant",content:response.answer,
        created_at:new Date().toISOString(),results:response.results,dataTimestamp:response.data_timestamp,warnings:response.warnings}]);
      setConversations(current=>current.some(item=>item.id===response.conversation_id)?current:
        [{id:response.conversation_id,title:clean.slice(0,80),created_at:new Date().toISOString(),updated_at:new Date().toISOString(),message_count:2},...current]);
    }catch(reason){setError(friendlyError(reason));setInput(clean);setMessages(current=>current.filter(item=>item.id!==userMessage.id));}
    finally{setPending(false);}};
  const submit=(event:FormEvent)=>{event.preventDefault();void send(input);};
  const startNew=()=>{if(pending)return;setConversationId(undefined);setMessages([]);setInput("");setError(undefined);};

  return <section className="assistant-page" aria-labelledby="assistant-title">
    <header className="assistant-hero"><div><p className="assistant-kicker"><Sparkles size={15}/> Live campus intelligence</p>
      <h1 id="assistant-title">Campus Assistant</h1>
      <p>Ask for live room details, compare spaces, or get a calm recommendation for where to go next.</p></div>
      <aside><Clock3 size={18}/><span><strong>Privacy-first and current</strong>Answers use the latest trusted OccupAI readings. Availability can change.</span></aside>
    </header>
    <div className="assistant-layout">
      <aside className="assistant-history" aria-label="Conversation history"><button type="button" onClick={startNew}>+ New conversation</button>
        <h2>Recent conversations</h2>{conversations.length?<ul>{conversations.map(item=><li key={item.id}><button type="button" aria-current={item.id===conversationId?"page":undefined} onClick={()=>void openConversation(item.id)}>{item.title||"Campus conversation"}<span>{item.message_count} messages</span></button></li>)}</ul>:<p>Your conversations will appear here.</p>}
      </aside>
      <div className="assistant-chat">
        <div className="assistant-messages" aria-live="polite" aria-busy={pending||loadingHistory}>
          {loadingHistory?<div className="assistant-status" role="status"><LoaderCircle className="spin"/> Restoring your conversation…</div>:
          messages.length===0?<div className="assistant-empty"><span><Bot size={30}/></span><h2>Find your best campus space</h2><p>Ask a question below or choose a suggestion to begin.</p></div>:
          messages.map(message=><article className={`assistant-message assistant-message--${message.role}`} key={message.id}>
            <span className="assistant-message__icon">{message.role==="user"?<User size={17}/>:<Bot size={18}/>}</span><div><b>{message.role==="user"?"You":"Campus Assistant"}</b><p>{message.content}</p>
              {message.role==="assistant"&&message.results&&<ResultCards results={message.results}/>} 
              {message.warnings?.length?<div className="assistant-warnings" role="note"><AlertTriangle size={16}/><ul>{message.warnings.map(warning=><li key={warning}>{warning}</li>)}</ul></div>:null}
              {message.dataTimestamp?<time dateTime={message.dataTimestamp}>Data updated {displayTimestamp(message.dataTimestamp)}</time>:null}
            </div></article>)}
          {pending?<div className="assistant-status" role="status"><LoaderCircle className="spin"/> Checking trusted live data…</div>:null}<div ref={endRef}/>
        </div>
        {error?<div className="assistant-error" role="alert"><span>{error}</span>{lastQuestion?<button type="button" disabled={pending} onClick={()=>void send(lastQuestion)}><RotateCcw size={15}/> Retry</button>:null}</div>:null}
        <div className="assistant-suggestions" aria-label="Suggested questions">{suggestions.map(question=><button type="button" key={question} disabled={pending} onClick={()=>setInput(question)}>{question}</button>)}</div>
        <form className="assistant-composer" onSubmit={submit}><label htmlFor="assistant-question">Ask Campus Assistant</label><div><textarea id="assistant-question" value={input} maxLength={1000} rows={2} disabled={pending} placeholder="Where can I find a quiet room right now?" onChange={event=>setInput(event.target.value)} onKeyDown={event=>{if(event.key==="Enter"&&!event.shiftKey){event.preventDefault();event.currentTarget.form?.requestSubmit();}}}/>
          <button type="submit" disabled={pending||!input.trim()}>{pending?<LoaderCircle className="spin"/>:<Send/>}<span>{pending?"Sending":"Send"}</span></button></div><small>Enter to send · Shift + Enter for a new line</small></form>
      </div>
    </div>
  </section>;
}
