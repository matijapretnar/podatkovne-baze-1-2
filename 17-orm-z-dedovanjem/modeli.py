import baza
import sqlite3

conn = sqlite3.connect('filmi.db')
baza.ustvari_bazo_ce_ne_obstaja(conn)
conn.execute('PRAGMA foreign_keys = ON')

class Zapis:
    privzete_vrednosti = {}

    def __init__(self, **kwargs):
        self.id = None
        for stolpec in self.stolpci:
            if stolpec in kwargs:
                setattr(self, stolpec, kwargs[stolpec])
            elif stolpec in self.privzete_vrednosti:
                setattr(self, stolpec, self.privzete_vrednosti[stolpec])
            else:
                raise ValueError(
                    'V konstruktorju {} je argument {} obvezen'.format(
                        self.__class__.__name__, stolpec
                    )
            )

    def __repr__(self):
        return "<{} '{}' (#{})>".format(self.__class__.__name__, self, self.id if self.id else '???')

    @staticmethod
    def relacija(drugi_zapis, povezovalna_tabela, moj_stolpec, drugi_stolpec):
        def metoda(self):
            razred_drugega_zapisa = eval(drugi_zapis)
            poizvedba = """
                SELECT {0}.* FROM {0} JOIN {1} ON {0}.id = {1}.{2} WHERE {1}.{3} = ?
            """.format(
                razred_drugega_zapisa.ime_tabele,
                povezovalna_tabela,
                drugi_stolpec,
                moj_stolpec
            )
            with conn:
                for vrstica in conn.execute(poizvedba, [self.id]):
                    yield razred_drugega_zapisa._preberi_vrstico(vrstica)
        return metoda


    @classmethod
    def _preberi_vrstico(cls, vrstica):
        id, *vrednosti = vrstica
        kwargs = dict(zip(cls.stolpci, vrednosti))
        zapis = cls(**kwargs)
        zapis.id = id
        return zapis
    
    def _shrani_kot_novo_vrstico(self):
        assert self.id is None
        staknjeni_stolpci = ', '.join(self.stolpci)
        vprasaji = ', '.join('?' for _ in self.stolpci)
        poizvedba = """
            INSERT INTO {} ({}) VALUES ({})
        """.format(self.ime_tabele, staknjeni_stolpci, vprasaji)
        parametri = [getattr(self, stolpec) for stolpec in self.stolpci]
        with conn:
            cur = conn.execute(poizvedba, parametri)
            self.id = cur.lastrowid

    def _posodobi_obstojeco_vrstico(self):
        assert self.id is not None
        posodobitve = ', '.join('{} = ?'.format(stolpec) for stolpec in self.stolpci)
        poizvedba = """
            UPDATE {} SET {} WHERE id = ?
        """.format(self.ime_tabele, posodobitve)
        parametri = [getattr(self, stolpec) for stolpec in self.stolpci]
        parametri.append(self.id)
        with conn:
            conn.execute(poizvedba, parametri)

    def shrani(self):
        if self.id is None:
            self._shrani_kot_novo_vrstico()
        else:
            self._posodobi_obstojeco_vrstico()

    def pobrisi(self):
        if self.id is None:
            raise ValueError(
                '{} ne obstaja, zato ga ne morem pobrisati'.format(
                    self.ednina.capitalize()
                )
            )
        else:
            poizvedba = """
                DELETE FROM {} WHERE id = ?
            """.format(self.ime_tabele)
            with conn:
                conn.execute(poizvedba, [self.id])

    @classmethod
    def poisci_vse(cls, **kwargs):
        stolpci = []
        vrednosti = []
        for stolpec, vrednost in kwargs.items():
            stolpci.append(stolpec)
            vrednosti.append(vrednost)
        where = ' AND '.join('{} = ?'.format(stolpec) for stolpec in stolpci)
        poizvedba = """
            SELECT * FROM {} WHERE {}
        """.format(cls.ime_tabele, where)
        with conn:
            for vrstica in conn.execute(poizvedba, vrednosti):
                yield cls._preberi_vrstico(vrstica)

    @classmethod
    def poisci_enega(cls, **kwargs):
        rezultati = cls.poisci_vse(**kwargs)
        prvi = next(rezultati, None)
        naslednji = next(rezultati, None)
        if prvi is None:
            raise ValueError(
                '{} z danimi podatki ne obstaja'.format(
                    cls.ime_tabele
                )
            )
        elif naslednji is None:
            return prvi
        else:
            raise ValueError(
                '{} z danimi podatki ni natanko določen'.format(
                    cls.ime_tabele
                )
            )



class Zanr(Zapis):
    ime_tabele = 'zanr'
    ednina = 'žanr'
    mnozina = 'žanri'
    stolpci = [
        'naziv',
    ]
    filmi = Zapis.relacija(drugi_zapis='Film', povezovalna_tabela='pripada', moj_stolpec='zanr', drugi_stolpec='film')

    def __str__(self):
        return self.naziv


class Film(Zapis):
    ime_tabele = 'film'
    ednina = 'film'
    mnozina = 'filmi'
    stolpci = [
        'naslov',
        'dolzina',
        'leto',
        'ocena',
        'metascore',
        'glasovi',
        'zasluzek',
        'opis',
    ]
    privzete_vrednosti = {
        'ocena': None,
        'metascore': None,
        'glasovi': None,
        'zasluzek': None,
        'opis': '',
    }
    zanri = Zapis.relacija(drugi_zapis='Zanr', povezovalna_tabela='pripada', moj_stolpec='film', drugi_stolpec='zanr')
    osebe = Zapis.relacija(drugi_zapis='Oseba', povezovalna_tabela='nastopa', moj_stolpec='film', drugi_stolpec='oseba')

    def __str__(self):
        return '{} ({})'.format(self.naslov, self.leto)

class Oseba(Zapis):
    ime_tabele = 'oseba'
    ednina = 'oseba'
    mnozina = 'osebe'
    stolpci = [
        'ime',
    ]
    filmi = Zapis.relacija(drugi_zapis='Film', povezovalna_tabela='nastopa', moj_stolpec='oseba', drugi_stolpec='film')

    def __str__(self):
        return self.ime


##################################################################

filmi_2010 = Film.poisci_vse(leto=2010, ocena=6.7)
assert next(filmi_2010).naslov == 'Ljubezen in druge droge'
assert next(filmi_2010).naslov == 'Robin Hood'
assert next(filmi_2010).leto == 2010

avatar = Film.poisci_enega(naslov='Avatar')
assert avatar.naslov == 'Avatar'
assert avatar.ocena == 7.8

avatar.ocena = 7.9
avatar.shrani()
assert len(list(Film.poisci_vse(naslov='Avatar'))) == 1
avatar.ocena = 7.8
avatar.shrani()
assert len(list(Film.poisci_vse(naslov='Avatar'))) == 1

assert {zanr.naziv for zanr in avatar.zanri()} == {'Fantasy', 'Adventure', 'Action'}


ime_predmeta = 'Podatkovne baze 1'
podatkovne_baze_1 = Film(naslov=ime_predmeta, dolzina=2000, leto=2018, zasluzek=0)
podatkovne_baze_1.shrani()
assert len(list(Film.poisci_vse(naslov=ime_predmeta))) == 1
podatkovne_baze_1.pobrisi()
assert len(list(Film.poisci_vse(naslov=ime_predmeta))) == 0

for zanr in avatar.zanri():
    print(zanr)
    for _, film in zip(range(10), zanr.filmi()):
        print('-', film)

lepi_leonardo = Oseba.poisci_enega(ime='Leonardo DiCaprio')
for film in lepi_leonardo.filmi():
    print(film)
    for soigralec_lepega_leonarda in film.osebe():
        print('-', soigralec_lepega_leonarda)
