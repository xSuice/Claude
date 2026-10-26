class RingPuffer:
    def __init__(self, kapazitaet):
        if type(kapazitaet) is not int or kapazitaet < 1:
            raise ValueError('kapazitaet')
        self.kapazitaet, self._d = kapazitaet, []
    def append(self, x):
        self._d.append(x)
        if len(self._d) > self.kapazitaet: self._d.pop(0)
    def extend(self, it):
        for x in it: self.append(x)
    def __len__(self): return len(self._d)
    def __iter__(self): return iter(list(self._d))
    def __getitem__(self, i):
        if isinstance(i, slice): raise TypeError('slice')
        return self._d[i]
    @property
    def voll(self): return len(self._d) == self.kapazitaet
    def leeren(self): self._d.clear()
    def entnehmen(self): return self._d.pop(0)
    def __repr__(self): return f'RingPuffer(kapazitaet={self.kapazitaet}, elemente={self._d})'
    def __eq__(self, o): return isinstance(o, RingPuffer) and (self.kapazitaet, self._d) == (o.kapazitaet, o._d)
