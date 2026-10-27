import math,re
def tokens(text,n=2):
 s=re.sub(r"\s+","",text.lower());return [s[i:i+n] for i in range(max(0,len(s)-n+1))]
def vectors(texts):
 docs=[tokens(x) for x in texts];df={}
 for ts in docs:
  for t in set(ts):df[t]=df.get(t,0)+1
 out=[]
 for ts in docs:
  tf={}
  for t in ts:tf[t]=tf.get(t,0)+1
  out.append({t:(1+math.log(v))*(math.log((1+len(docs))/(1+df[t]))+1) for t,v in tf.items()})
 return out
def cosine(a,b):
 if not a or not b:return 0.0
 dot=sum(v*b.get(k,0) for k,v in a.items());na=math.sqrt(sum(v*v for v in a.values()));nb=math.sqrt(sum(v*v for v in b.values()))
 return dot/(na*nb) if na and nb else 0.0
