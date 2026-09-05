import { motion } from "framer-motion";
import { ArrowRight, BarChart3, Eye, Layers3, LockKeyhole, Route, Sparkles } from "lucide-react";
import { Link } from "react-router-dom";

const reveal = { initial: { opacity: 0, y: 54, scale: .97 }, whileInView: { opacity: 1, y: 0, scale: 1 }, viewport: { once: false, amount: .22 }, transition: { duration: .7, ease: [0.2, 0.8, 0.2, 1] as [number, number, number, number] } };

export function WelcomePage() {
  return <div className="welcome-page">
    <header className="welcome-nav">
      <Link className="welcome-brand" to="/"><img src="/occupai-logo.png" alt=""/><span>Occup<span>AI</span></span></Link>
      <nav aria-label="Welcome navigation"><a href="#vision">Vision</a><a href="#intelligence">Intelligence</a><Link to="/login">Log in</Link><Link className="welcome-nav__cta" to="/login?mode=signup">Get started <ArrowRight size={15}/></Link></nav>
    </header>
    <main>
      <section className="welcome-hero">
        <div className="welcome-hero__copy">
          <motion.p {...reveal} className="welcome-kicker"><Sparkles size={15}/> Campus intelligence, beautifully clear</motion.p>
          <motion.h1 {...reveal} transition={{...reveal.transition, delay:.08}}>Space that<br/><em>understands</em> people.</motion.h1>
          <motion.p {...reveal} transition={{...reveal.transition, delay:.16}} className="welcome-lede">OccupAI turns live occupancy signals into confident decisions—helping every room, floor, and building work better.</motion.p>
          <motion.div {...reveal} transition={{...reveal.transition, delay:.24}} className="welcome-actions"><Link className="welcome-primary" to="/login?mode=signup">Explore OccupAI <ArrowRight size={18}/></Link><Link className="welcome-secondary" to="/login">View live dashboard</Link></motion.div>
          <motion.div {...reveal} className="welcome-trust"><span><i/>Privacy-first sensing</span><span><i/>Live operational data</span><span><i/>Actionable recommendations</span></motion.div>
        </div>
        <motion.div initial={{opacity:0,x:70,rotate:2}} whileInView={{opacity:1,x:0,rotate:0}} viewport={{once:false,amount:.2}} transition={{duration:1,ease:[.2,.8,.2,1]}} className="welcome-hero__visual"><img src="/aust-campus.jpg" alt="Ahsanullah University of Science and Technology campus in Tejgaon, Dhaka"/><span className="campus-photo-label">AUST · Tejgaon, Dhaka</span><span className="floating-stat floating-stat--one"><b>42%</b> campus utilization</span><span className="floating-stat floating-stat--two"><i/> 128 rooms live</span></motion.div>
      </section>

      <section className="welcome-ideas" id="vision">
        <motion.div {...reveal} className="welcome-section-title"><p>One intelligent layer</p><h2>From presence to possibility.</h2><span>OccupAI connects what is happening now with what your campus should do next.</span></motion.div>
        <div className="idea-grid">
          {[{icon:Eye,n:"01",title:"Sense",text:"Understand occupancy in real time without identifying individuals."},{icon:BarChart3,n:"02",title:"Understand",text:"Reveal demand, quiet periods, capacity pressure, and reliable trends."},{icon:Route,n:"03",title:"Act",text:"Guide people to better spaces and help teams operate buildings efficiently."}].map(({icon:Icon,n,title,text},i)=><motion.article {...reveal} transition={{...reveal.transition,delay:i*.08}} key={title}><span>{n}</span><Icon size={25}/><h3>{title}</h3><p>{text}</p></motion.article>)}
        </div>
      </section>

      <section className="welcome-showcase" id="intelligence">
        <motion.div {...reveal} className="welcome-showcase__image"><img src="/aust-campus-courtyard.jpg" alt="Open internal courtyard at Ahsanullah University of Science and Technology"/><span>Inside AUST · A connected campus</span></motion.div>
        <motion.div {...reveal} className="welcome-showcase__copy"><p className="welcome-kicker"><Layers3 size={15}/> A living digital layer</p><h2>See the whole campus. Notice what matters.</h2><p>Move from a floor-level pulse to room-level detail, uncover patterns over time, and receive clear recommendations while the data is still useful.</p><ul><li><span><Eye size={18}/></span><div><b>Live floor visibility</b><small>Explore every monitored room through a responsive visual map.</small></div></li><li><span><BarChart3 size={18}/></span><div><b>Informed analytics</b><small>Compare peaks, averages, coverage, and utilization over time.</small></div></li><li><span><LockKeyhole size={18}/></span><div><b>Privacy by design</b><small>Count presence and movement without recognizing identities.</small></div></li></ul></motion.div>
      </section>

      <motion.section {...reveal} className="welcome-final"><div><p>Ready to see space differently?</p><h2>Make every square metre count.</h2></div><Link to="/login?mode=signup">Get started <ArrowRight size={18}/></Link></motion.section>
    </main>
    <footer className="welcome-footer"><Link className="welcome-brand" to="/"><img src="/occupai-logo.png" alt=""/><span>Occup<span>AI</span></span></Link><span>Privacy-first campus intelligence.</span><span>© 2026 OccupAI</span></footer>
  </div>;
}
