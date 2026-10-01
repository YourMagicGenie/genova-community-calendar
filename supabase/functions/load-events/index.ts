import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import {
  canDeleteStaleEvents,
  loadEventsCorsHeaders,
  validateLoadEventsBody,
  withLoadEventsProtection,
} from "./protection.mjs";

const corsHeaders = {
  ...loadEventsCorsHeaders,
};

Deno.serve(withLoadEventsProtection(async (_req, body) => {
  try {
    const supabaseUrl = Deno.env.get("SUPABASE_URL")!;
    const supabaseServiceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
    const supabase = createClient(supabaseUrl, supabaseServiceKey);

    // --- Direct POST mode: CI sends {city, events} per city ---
    if (body.mode === "direct") {
      const city = body.city;
      const events = body.events;
      console.log(`Direct POST: ${events.length} events for ${city}`);

      const uniqueEvents = new Map();
      for (const event of events) {
        if (event.source_uid && !uniqueEvents.has(event.source_uid)) {
          uniqueEvents.set(event.source_uid, event);
        }
      }
      console.log(`Unique events for ${city}: ${uniqueEvents.size}`);

      const batchSize = 500;
      const eventsArray = Array.from(uniqueEvents.values());
      let inserted = 0;
      let errors = 0;
      const errorDetails: string[] = [];

      for (let i = 0; i < eventsArray.length; i += batchSize) {
        const batchNum = i / batchSize;
        const batch = eventsArray.slice(i, i + batchSize);
        let lastError: any = null;

        // Retry each batch up to 3 times for transient failures
        for (let attempt = 0; attempt < 3; attempt++) {
          const { error } = await supabase
            .from("events")
            .upsert(batch, { onConflict: "source_uid", ignoreDuplicates: false });
          if (!error) {
            inserted += batch.length;
            lastError = null;
            break;
          }
          lastError = error;
          console.error(`Batch ${batchNum} attempt ${attempt + 1} error:`, JSON.stringify(error));
          if (attempt < 2) {
            await new Promise(r => setTimeout(r, 1000 * (attempt + 1)));
          }
        }
        if (lastError) {
          errors += batch.length;
          errorDetails.push(`batch ${batchNum}: ${lastError.message || JSON.stringify(lastError)}`);
        }
      }

      // Remove stale events for this city that are no longer in the feed
      // Uses RPC to avoid URL length limits with large IN lists
      const newSourceUids = Array.from(uniqueEvents.keys());
      let deleted = 0;
      if (canDeleteStaleEvents(errors) && newSourceUids.length > 0) {
        const { data: delCount, error: delError } = await supabase
          .rpc("delete_stale_events", { p_city: city, p_source_uids: newSourceUids });
        if (delError) {
          console.error(`Cleanup ${city} error:`, delError);
          errorDetails.push(`cleanup: ${delError.message}`);
        } else {
          deleted = delCount || 0;
        }
      }
      if (deleted > 0) {
        console.log(`Cleaned up ${deleted} stale events for ${city}`);
      }

      const result: any = { success: errors === 0, city, fetched: events.length, unique: uniqueEvents.size, deleted, inserted, errors };
      if (errorDetails.length > 0) {
        result.errorDetails = errorDetails;
      }
      console.log("Result:", result);
      return new Response(JSON.stringify(result), {
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    // --- Legacy mode: fetch events.json from GitHub for each city ---
    const ghRepo = "YourMagicGenie/genova-community-calendar";
    const RAW_BASE = `https://raw.githubusercontent.com/${ghRepo}/main/cities`;
    const cities: string[] = body.cities;

    console.log(`Processing cities: ${cities.join(", ")}`);

    // Collect events per city for stale cleanup after upsert
    const allEvents: any[] = [];
    const eventsByCity = new Map<string, string[]>(); // city -> source_uids
    for (const city of cities) {
      const url = `${RAW_BASE}/${city}/events.json`;
      console.log(`Fetching events from ${city}:`, url);
      try {
        const response = await fetch(url);
        if (!response.ok) {
          console.error(`Failed to fetch ${city}: ${response.status}`);
          continue;
        }
        const events = await response.json();
        const validated = validateLoadEventsBody({ city, events });
        if (validated.error) {
          console.error(`Rejected ${city} feed:`, validated.error);
          continue;
        }
        const genovaEvents = validated.value.events;
        const cityUids: string[] = [];
        for (const event of genovaEvents) {
          if (event.source_uid) cityUids.push(event.source_uid);
        }
        eventsByCity.set(city, cityUids);
        allEvents.push(...genovaEvents);
        console.log(`Fetched ${genovaEvents.length} events from ${city}`);
      } catch (e) {
        console.error(`Error fetching ${city}:`, e);
      }
    }
    console.log(`Total fetched: ${allEvents.length} events`);

    const uniqueEvents = new Map();
    for (const event of allEvents) {
      if (event.source_uid && !uniqueEvents.has(event.source_uid)) {
        uniqueEvents.set(event.source_uid, event);
      }
    }
    console.log(`Unique events: ${uniqueEvents.size}`);

    const batchSize = 500;
    const eventsArray = Array.from(uniqueEvents.values());
    let inserted = 0;
    let errors = 0;
    const errorDetails: string[] = [];

    for (let i = 0; i < eventsArray.length; i += batchSize) {
      const batchNum = i / batchSize;
      const batch = eventsArray.slice(i, i + batchSize);
      let lastError: any = null;

      for (let attempt = 0; attempt < 3; attempt++) {
        const { error } = await supabase
          .from("events")
          .upsert(batch, { onConflict: "source_uid", ignoreDuplicates: false });
        if (!error) {
          inserted += batch.length;
          lastError = null;
          break;
        }
        lastError = error;
        console.error(`Batch ${batchNum} attempt ${attempt + 1} error:`, JSON.stringify(error));
        if (attempt < 2) {
          await new Promise(r => setTimeout(r, 1000 * (attempt + 1)));
        }
      }
      if (lastError) {
        errors += batch.length;
        errorDetails.push(`batch ${batchNum}: ${lastError.message || JSON.stringify(lastError)}`);
      }
    }

    // Remove stale events per city using RPC to avoid URL length limits
    let deleted = 0;
    for (const [city, uids] of eventsByCity) {
      if (canDeleteStaleEvents(errors) && uids.length > 0) {
        const { data: delCount, error: delError } = await supabase
          .rpc("delete_stale_events", { p_city: city, p_source_uids: uids });
        if (delError) {
          console.error(`Cleanup ${city} error:`, delError);
        } else {
          deleted += delCount || 0;
        }
      }
    }
    if (deleted > 0) {
      console.log(`Cleaned up ${deleted} stale events`);
    }

    const result: any = { success: errors === 0, fetched: allEvents.length, unique: uniqueEvents.size, deleted, inserted, errors };
    if (errorDetails.length > 0) {
      result.errorDetails = errorDetails;
    }
    console.log("Result:", result);
    return new Response(JSON.stringify(result), {
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  } catch (error) {
    console.error("Error:", error);
    return new Response(
      JSON.stringify({ success: false, error: error.message }),
      { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }
}, () => Deno.env.get("LOAD_EVENTS_TOKEN")));
