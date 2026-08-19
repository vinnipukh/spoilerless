# Spoiler-Free IMDb — Proje Planı & Memgraph Şeması

## 1. Temel Prensip: "Reveal Point" (Açığa Çıkma Noktası)

Sistemin can alıcı noktası şu: **her spoiler olabilecek veri parçasına, o bilginin "güvenli" hale geldiği bir bölüm sırası (`safe_at_order`) damgası vurulur.** Her sorgu, kullanıcının o dizideki izleme ilerlemesiyle bu değeri karşılaştırıp filtreler.

```
göster(veri) = eğer veri.safe_at_order <= kullanici.izleme_ilerlemesi ise göster, değilse gizle/genellikle
```

Bu tek kural; oyuncu bölüm sayısını, karakter durumunu (öldü mü, ayrıldı mı), bölüm başlıklarını, trivia'ları, yorumları ve puanları aynı mantıkla kapsar. Graph DB'yi seçmenin asıl faydası burada: ilişkiler (`ACTED_AS`, `APPEARS_IN`, `RELATIONSHIP_WITH`) üzerine bu damgayı property olarak koyup, Cypher'da tek bir `WHERE` cümlesiyle her yerde tekrar kullanabiliyorsun.

**Kullanıcı ilerlemesi nasıl hesaplanır?** İki seçenek var:
- **Basit (önerilen MVP):** `en yüksek izlenen air_order` — hızlı ama kullanıcı bölüm atlarsa (3'ü izlemeden 7'yi işaretlerse) sorun çıkarır.
- **Güvenli:** `en yüksek KESINTISIZ izlenen air_order` (1'den başlayıp ilk boşluğa kadar) — atlanan bölümlerdeki bilgi asla "izlendi" sayılmaz. Spoiler'dan kaçınma amacı için bu daha doğru; MVP sonrası buna geçilmeli.

---

## 2. Graph Şeması

### Node (Düğüm) Tipleri

| Label | Önemli Property'ler |
|---|---|
| **Show** | id, title, type (movie/tv), start_year, end_year, synopsis_short (spoiler'sız logline) |
| **Season** | id, season_number |
| **Episode** | id, air_order (global, sezon bağımsız sıra), episode_number_in_season, air_date, runtime, title, **title_is_spoiler** (bool), synopsis (yalnızca izlenince gösterilir) |
| **Person** | id, name, birth_year, photo_url |
| **Character** | id, name, **last_appearance_order** (ayrılış/ölüm noktası — gated), status (alive/dead/unknown), photo_url |
| **Genre** | id, name |
| **User** | id, username |
| **Review** | id, body, created_at, **spoiler_up_to_order** (yazarın belirttiği, incelemenin hangi bölüme kadar bilgi içerdiği) |
| **Trivia** | id, text, **safe_at_order** |

### Relationship (İlişki) Tipleri

```
(Show)-[:HAS_SEASON]->(Season)
(Season)-[:HAS_EPISODE]->(Episode)
(Episode)-[:NEXT]->(Episode)                         // global air_order zinciri
(Person)-[:ACTED_AS {character_id}]->(Character)
(Character)-[:APPEARS_IN {order}]->(Episode)          // order = episode.air_order, hızlı filtre için
(Person)-[:DIRECTED]->(Episode)
(Person)-[:WROTE]->(Episode)
(Show)-[:HAS_GENRE]->(Genre)
(Character)-[:RELATIONSHIP_WITH {type, revealed_at_order}]->(Character)   // akrabalık, romantik ilişki vb — gated
(User)-[:FOLLOWS]->(Show)
(User)-[:WATCHED {watched_at}]->(Episode)
(User)-[:PROGRESS {last_contiguous_order}]->(Show)    // önbelleklenmiş ilerleme göstergesi
(User)-[:RATED {score}]->(Episode)                    // sadece izlenen bölüme puan verilebilir
(User)-[:WROTE_REVIEW]->(Review)-[:ABOUT]->(Episode)
(Trivia)-[:ABOUT]->(Show|Episode|Character|Person)
```

**Kritik tasarım kararı:** `Person-[:ACTED_AS]->Character` ilişkisinde toplam bölüm sayısını **asla statik bir property olarak tutma**. Bu bilgi her zaman `APPEARS_IN` kenarları üzerinden, kullanıcının ilerlemesine göre canlı hesaplanmalı. Aksi halde "oyuncu 24 bölümden sadece 5'inde göründü" gibi bir alan bile, o oyuncunun erken ayrılacağının ipucu olur.

---

## 3. Örnek Cypher Sorguları

### a) Kullanıcının bir dizideki ilerlemesi
```cypher
MATCH (u:User {id:$userId})-[p:PROGRESS]->(s:Show {id:$showId})
RETURN p.last_contiguous_order AS progress
```

### b) Oyuncu sayfası — dinamik bölüm sayısı (spoiler'sız)
```cypher
MATCH (u:User {id:$userId})-[prog:PROGRESS]->(s:Show {id:$showId})
MATCH (p:Person {id:$personId})-[:ACTED_AS]->(c:Character)-[:APPEARS_IN]->(e:Episode)
      <-[:HAS_EPISODE]-(:Season)<-[:HAS_SEASON]-(s)
WHERE e.air_order <= prog.last_contiguous_order
RETURN c.name AS character, count(e) AS episodes_seen_so_far
```
Toplam planlanan bölüm sayısı asla dönmez — yalnızca "şu ana kadar kaç bölümde göründü" bilgisi verilir.

### c) Karakterin durumu (öldü/hayatta) — kilitli alan
```cypher
MATCH (c:Character {id:$characterId})<-[:HAS_SEASON|HAS_EPISODE*]-(s:Show)
MATCH (u:User {id:$userId})-[prog:PROGRESS]->(s)
RETURN CASE
  WHEN c.last_appearance_order IS NOT NULL AND c.last_appearance_order <= prog.last_contiguous_order
  THEN c.status ELSE 'unknown'
END AS status
```

### d) Bölüm listesi — spoiler başlıkları maskelenir
```cypher
MATCH (s:Show {id:$showId})-[:HAS_SEASON]->(:Season)-[:HAS_EPISODE]->(e:Episode)
MATCH (u:User {id:$userId})-[prog:PROGRESS]->(s)
RETURN e.air_order,
  CASE WHEN e.air_order <= prog.last_contiguous_order OR NOT e.title_is_spoiler
       THEN e.title ELSE 'Bölüm ' + toString(e.episode_number_in_season) END AS title,
  CASE WHEN e.air_order <= prog.last_contiguous_order THEN e.synopsis ELSE null END AS synopsis
ORDER BY e.air_order
```

### e) "Bunu izleyenler şunu da izledi" (graph'ın asıl gücü)
```cypher
MATCH (u:User {id:$userId})-[:WATCHED]->(:Episode)<-[:HAS_EPISODE]-(:Season)<-[:HAS_SEASON]-(s:Show)
MATCH (other:User)-[:WATCHED]->(:Episode)<-[:HAS_EPISODE]-(:Season)<-[:HAS_SEASON]-(s)
WHERE other <> u
MATCH (other)-[:WATCHED]->(:Episode)<-[:HAS_EPISODE]-(:Season)<-[:HAS_SEASON]-(rec:Show)
WHERE NOT (u)-[:FOLLOWS]->(rec)
RETURN rec.title, count(DISTINCT other) AS ortak_izleyici
ORDER BY ortak_izleyici DESC LIMIT 10
```

---

## 4. Faz Bazlı Proje Planı

**Faz 0 — Kapsam & Veri Kaynağı**
- Spoiler tuzaklarının tam envanteri (bkz. §5)
- Veri kaynağı: TMDb/OMDb API'den import mu, manuel giriş mi (ToS kontrolü şart)
- Memgraph'ı Docker ile lokal ayağa kaldırma

**Faz 1 — MVP**
- Şema: Show, Season, Episode, Person, Character, User
- Basit auth + `WATCHED` işaretleme
- Dizi detay sayfası + bölüm listesi (izlenmemiş bölüm = kilitli/genel başlık)

**Faz 2 — Spoiler Motoru**
- `ACTED_AS` / `APPEARS_IN` ilişkileri
- Dinamik bölüm sayısı hesaplama, karakter durumu gating
- `last_contiguous_order` hesaplama mantığı (atlanan bölüm kontrolü)

**Faz 3 — Sosyal Katman**
- Review/Rating + zorunlu spoiler etiketleme (`spoiler_up_to_order`)
- Takip listesi, graph tabanlı öneri sorguları

**Faz 4 — İleri Spoiler Koruması**
- Trivia gating, karakter ilişki gating (`RELATIONSHIP_WITH.revealed_at_order`)
- Arama/otomatik tamamlamada spoiler filtreleme
- Görsel materyal (poster/thumbnail) kontrolü

**Faz 5 — Performans**
- Memgraph'ta `id` alanlarına index/constraint
- Sık sorgular için cache (Redis)
- `WHERE` filtrelerini traversal'ın en erken noktasına taşıma (Memgraph query planı optimizasyonu)

---

## 5. Spoiler Tuzakları Kontrol Listesi

Bunların her biri sisteme girmeden önce "bu neyi ele veriyor?" diye sorgulanmalı:

- Bölüm başlıkları (ör. bir karakterin adını taşıyan "final" bölümü)
- Anormal bölüm/sezon süresi (uzun final bölümü ipucu verir)
- Oyuncunun toplam/kalan bölüm sayısı
- Cast sıralaması değişimi ("starring" listesine sonradan eklenme)
- Karakterin başrol/yardımcı statüsü
- Karakter ölüm/ayrılış durumu
- Karakterler arası gizli ilişki (sürpriz akrabalık, ihanet vb.)
- Trivia / "biliyor muydunuz" içerikleri
- Kullanıcı yorumları ve **ortalama puanlar** (finale bölümünün ortalama puanı bile ipucu olabilir — puan da izlenen bölüme göre canlı hesaplanmalı)
- Görsel materyaller (poster, thumbnail — final sezon posterinde bir karakter yoksa bu bile ipucudur)
- Arama otomatik tamamlama önerileri
- "Gelecek bölüm/sezon" tanıtımları
- Ödül/nominasyon bilgileri (finale ödül kazandıysa yayın sonrası hemen görünür)
- Dış bağlantılar / wiki linkleri

---

## 6. Teknoloji Yığını Önerisi

- **DB:** Memgraph (Docker), Bolt protokolü üzerinden
- **Backend:** Python + FastAPI + GQLAlchemy, ya da Node.js + `neo4j-driver` (Memgraph Bolt uyumlu)
- **Frontend:** React/Next.js
- **Auth:** JWT
- **Cache:** Redis (Faz 5)

---

## 7. Açık Kalan Kararlar (senin belirlemen gereken)

- Bölüm atlama diye bir özellik/ kullanıcıya alan bırakılmayacak. eğer bölüm 5 açılıyorsa bölüm 1-5 arasının açıldığı kullanıcıya belirtilecek
- Film serilerindeki her film bir bölüm olarak ele alınacak (star wars episode 1,2,3 ...)
- Yayın sırası önemli. Kronolojik sıra ile ilgilenmiyoruz. Bölüm 1 bölüm 5 ten sonraki bir olayı anlatıyorsa bile bölüm 1 'i işliyoruz'.

