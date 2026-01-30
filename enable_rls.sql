-- Enable Row Level Security on all tables
ALTER TABLE public.categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.resources ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.series ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.series_items ENABLE ROW LEVEL SECURITY;

-- Create policies to allow public (anon) READ access for data tables
CREATE POLICY "Allow public read access" ON public.categories FOR SELECT USING (true);
CREATE POLICY "Allow public read access" ON public.resources FOR SELECT USING (true);
CREATE POLICY "Allow public read access" ON public.series FOR SELECT USING (true);
CREATE POLICY "Allow public read access" ON public.series_items FOR SELECT USING (true);

-- Note: 'settings' table RLS is enabled but NO public policies are added,
-- meaning the public (anon) cannot read it. The bot (service_role) still can.

-- Note: The bot uses the 'service_role' key, which bypasses RLS.
-- This means the bot will still be able to SELECT, INSERT, UPDATE, and DELETE on all tables.
