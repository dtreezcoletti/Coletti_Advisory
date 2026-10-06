
function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "access-control-allow-origin": "*",
      "access-control-allow-headers": "authorization, x-client-info, apikey, content-type",
    },
  });
}
function parseNamedKey(envName: string, fallbackName: string): string {
  const raw = Deno.env.get(envName);
  if (raw) {
    try {
      const parsed = JSON.parse(raw);
      if (typeof parsed?.default === "string" && parsed.default) return parsed.default;
    } catch {}
  }
  return Deno.env.get(fallbackName) ?? "";
}
function publishableKey(): string { return parseNamedKey("SUPABASE_PUBLISHABLE_KEYS","SUPABASE_ANON_KEY"); }
function secretKey(): string { return parseNamedKey("SUPABASE_SECRET_KEYS","SUPABASE_SERVICE_ROLE_KEY"); }
function bearerToken(request: Request): string {
  const h=request.headers.get("authorization")??"";
  return h.startsWith("Bearer ")?h.slice(7).trim():"";
}
async function fetchJson(url:string,init:RequestInit){
  const response=await fetch(url,init); let body:any=null; try{body=await response.json();}catch{}
  return {response,body};
}
function serviceHeaders(extra:HeadersInit={}):HeadersInit {
  const key=secretKey();
  const h:Record<string,string>={apikey:key,"content-type":"application/json"};
  if(!key.startsWith("sb_secret_")) h.authorization=`Bearer ${key}`;
  return {...h,...(extra as Record<string,string>)};
}
function userHeaders(jwt:string):HeadersInit {
  const key=publishableKey();
  return {apikey:key,authorization:`Bearer ${jwt}`,"content-type":"application/json"};
}
function dollars(cents:number){ return new Intl.NumberFormat("en-US",{style:"currency",currency:"USD"}).format(cents/100); }
function appointmentLabel(startAt:string,timeZone:string){
  return new Intl.DateTimeFormat("en-US",{timeZone,dateStyle:"full",timeStyle:"short"}).format(new Date(startAt));
}
Deno.serve(async(request)=>{
  if(request.method==="OPTIONS") return new Response(null,{status:204,headers:{
    "access-control-allow-origin":"*","access-control-allow-headers":"authorization, x-client-info, apikey, content-type","access-control-allow-methods":"POST, OPTIONS"
  }});
  if(request.method!=="POST") return jsonResponse({error:"method_not_allowed"},405);
  const supabaseUrl=Deno.env.get("SUPABASE_URL")??"";
  const jwt=bearerToken(request);
  if(!supabaseUrl||!publishableKey()||!secretKey()) return jsonResponse({error:"supabase_not_configured"},503);
  if(!jwt) return jsonResponse({error:"authentication_required"},401);
  let body:any; try{body=await request.json();}catch{return jsonResponse({error:"invalid_json"},400);}
  const consultationId=String(body?.consultation_id??"").trim();
  if(!/^[0-9a-f-]{36}$/i.test(consultationId)) return jsonResponse({error:"valid_consultation_id_required"},400);

  const auth=await fetchJson(`${supabaseUrl}/auth/v1/user`,{headers:userHeaders(jwt)});
  if(!auth.response.ok||!auth.body?.id) return jsonResponse({error:"invalid_session"},401);
  const profile=await fetchJson(`${supabaseUrl}/rest/v1/profiles?id=eq.${encodeURIComponent(auth.body.id)}&select=id,role&limit=1`,{headers:userHeaders(jwt)});
  if(!profile.response.ok||profile.body?.[0]?.role!=="owner") return jsonResponse({error:"owner_authorization_required"},403);

  const wf=await fetchJson(`${supabaseUrl}/rest/v1/consultation_workflows?id=eq.${encodeURIComponent(consultationId)}&select=*&limit=1`,{headers:serviceHeaders()});
  const consultation=wf.body?.[0];
  if(!wf.response.ok||!consultation) return jsonResponse({error:"consultation_not_found"},404);
  if(consultation.confirmation_email_state==="SENT") return jsonResponse({ok:true,reused:true,provider_message_id:consultation.confirmation_email_provider_id});
  if(consultation.owner_decision!=="APPROVED_FOR_CONSULTATION"||!consultation.square_booking_id||!consultation.appointment_start) {
    return jsonResponse({error:"confirmed_square_appointment_required"},409);
  }
  if(!consultation.invoice_id) return jsonResponse({error:"consultation_invoice_required"},409);

  const inv=await fetchJson(`${supabaseUrl}/rest/v1/invoices?id=eq.${encodeURIComponent(consultation.invoice_id)}&select=*&limit=1`,{headers:serviceHeaders()});
  const invoice=inv.body?.[0];
  if(!inv.response.ok||!invoice||!invoice.payment_url) return jsonResponse({error:"square_payment_link_required"},409);

  const intakeReq=await fetchJson(`${supabaseUrl}/rest/v1/intake_submissions?id=eq.${encodeURIComponent(consultation.intake_id)}&select=id,contact&limit=1`,{headers:serviceHeaders()});
  const intake=intakeReq.body?.[0];
  const recipient=String(intake?.contact?.email??"").trim();
  if(!recipient||!recipient.includes("@")) return jsonResponse({error:"prospective_client_email_missing"},409);

  const resendKey=Deno.env.get("RESEND_API_KEY")??"";
  const from=Deno.env.get("COLETTI_TRANSACTIONAL_FROM")??"";
  const replyTo=(Deno.env.get("COLETTI_TRANSACTIONAL_REPLY_TO")??"").trim();
  if(!resendKey||!from) return jsonResponse({error:"transactional_email_not_configured"},503);

  const when=appointmentLabel(consultation.appointment_start,consultation.appointment_timezone||"America/Chicago");
  const fee=dollars(Number(invoice.amount_cents));
  const idempotencyKey=`consultation-confirmation:${consultation.id}:${consultation.appointment_start}`;

  const existing=await fetchJson(
    `${supabaseUrl}/rest/v1/consultation_notifications?idempotency_key=eq.${encodeURIComponent(idempotencyKey)}&select=*&limit=1`,
    {headers:serviceHeaders()}
  );
  if(existing.body?.[0]?.status==="SENT") return jsonResponse({ok:true,reused:true,provider_message_id:existing.body[0].provider_message_id});

  await fetchJson(`${supabaseUrl}/rest/v1/consultation_workflows?id=eq.${encodeURIComponent(consultation.id)}`,{
    method:"PATCH",headers:serviceHeaders({prefer:"return=minimal"}),body:JSON.stringify({confirmation_email_state:"SENDING",updated_at:new Date().toISOString()})
  });
  const notificationPayload={consultation_id:consultation.id,notification_type:"APPOINTMENT_CONFIRMATION",recipient_email:recipient,provider:"resend",status:"SENDING",idempotency_key:idempotencyKey,updated_at:new Date().toISOString()};
  if(existing.body?.[0]) {
    await fetchJson(`${supabaseUrl}/rest/v1/consultation_notifications?id=eq.${encodeURIComponent(existing.body[0].id)}`,{
      method:"PATCH",headers:serviceHeaders({prefer:"return=minimal"}),body:JSON.stringify(notificationPayload)
    });
  } else {
    await fetchJson(`${supabaseUrl}/rest/v1/consultation_notifications`,{
      method:"POST",headers:serviceHeaders({prefer:"return=minimal"}),body:JSON.stringify(notificationPayload)
    });
  }

  const subject="Your Coletti & Co. consultation is confirmed";
  const text=[
    "Your Coletti & Co. consultation appointment is confirmed.",
    "",
    `Appointment: ${when}`,
    `Consultation fee: ${fee}`,
    "",
    "The consultation fee is due in full before the consultation. Your appointment is not financially cleared until payment is recorded.",
    "",
    `Pay securely through Square: ${invoice.payment_url}`,
    "",
    "If the appointment must be changed, use the authorized scheduling process so the calendar and payment records remain reconciled.",
    "",
    "Coletti & Co.",
    "Discretion in our work. Integrity in our word."
  ].join("\n");
  const payload:any={from,to:[recipient],subject,text};
  if(replyTo) payload.reply_to=replyTo;

  const send=await fetchJson("https://api.resend.com/emails",{
    method:"POST",
    headers:{authorization:`Bearer ${resendKey}`,"content-type":"application/json","Idempotency-Key":idempotencyKey},
    body:JSON.stringify(payload)
  });

  if(!send.response.ok||!send.body?.id){
    const reason=JSON.stringify(send.body??{}).slice(0,1000);
    await fetchJson(`${supabaseUrl}/rest/v1/consultation_notifications?idempotency_key=eq.${encodeURIComponent(idempotencyKey)}`,{
      method:"PATCH",headers:serviceHeaders({prefer:"return=minimal"}),body:JSON.stringify({status:"FAILED",failure_reason:reason,updated_at:new Date().toISOString()})
    });
    await fetchJson(`${supabaseUrl}/rest/v1/consultation_workflows?id=eq.${encodeURIComponent(consultation.id)}`,{
      method:"PATCH",headers:serviceHeaders({prefer:"return=minimal"}),body:JSON.stringify({confirmation_email_state:"FAILED",updated_at:new Date().toISOString()})
    });
    return jsonResponse({error:"confirmation_email_failed"},502);
  }

  const now=new Date().toISOString();
  await fetchJson(`${supabaseUrl}/rest/v1/consultation_notifications?idempotency_key=eq.${encodeURIComponent(idempotencyKey)}`,{
    method:"PATCH",headers:serviceHeaders({prefer:"return=minimal"}),body:JSON.stringify({status:"SENT",provider_message_id:send.body.id,sent_at:now,failure_reason:null,updated_at:now})
  });
  await fetchJson(`${supabaseUrl}/rest/v1/consultation_workflows?id=eq.${encodeURIComponent(consultation.id)}`,{
    method:"PATCH",headers:serviceHeaders({prefer:"return=minimal"}),body:JSON.stringify({confirmation_email_state:"SENT",confirmation_email_provider_id:send.body.id,confirmation_email_sent_at:now,updated_at:now})
  });
  return jsonResponse({ok:true,reused:false,provider_message_id:send.body.id});
});
