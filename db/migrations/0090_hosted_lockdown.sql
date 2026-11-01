-- Hosted database lockdown (docs/deploy.md). Supabase creates the roles anon, authenticated and service_role
-- and, by default, grants them every table, sequence and function in schema public, so its REST API (the
-- "Data API") could read sign-in tokens, users and organizations with the project's anon key. The app never
-- uses that API: the engine connects directly. Take those grants away now and for tables made later.
-- On a database without those roles (local Docker, CI) this does nothing.
do $$
declare r text;
begin
  foreach r in array array['anon', 'authenticated', 'service_role'] loop
    if exists (select 1 from pg_roles where rolname = r) then
      execute format('revoke all on all tables in schema public from %I', r);
      execute format('revoke all on all sequences in schema public from %I', r);
      execute format('revoke all on all functions in schema public from %I', r);
      execute format('alter default privileges in schema public revoke all on tables from %I', r);
      execute format('alter default privileges in schema public revoke all on sequences from %I', r);
      execute format('alter default privileges in schema public revoke all on functions from %I', r);
    end if;
  end loop;
end
$$;
