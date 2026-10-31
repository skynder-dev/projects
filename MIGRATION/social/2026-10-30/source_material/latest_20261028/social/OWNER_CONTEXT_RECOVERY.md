# Owner-context interrupted-head recovery

Under the existing owner lock, an existing deterministic revision file may be
reused only if its bytes exactly equal the intended revision. Its fsync must succeed
before promotion, including when an earlier attempt failed at fsync. Divergent bytes
are preserved and rejected. The expected head is checked before the revision work
and again before the atomic head replacement; stale or malformed heads cannot be
promoted through this operation. Prior source/revision files are not overwritten.

Eight actual failure/concurrency tests run in owned temporary storage. They cover
failed head replacement, identical retry, divergent/noncanonical orphan rejection,
failed revision fsync/retry, stale parent, corrupt revision identifier, one external
head change before promotion, and two concurrent threads using Linux advisory locks.
This is not an atomic CAS against noncooperating filesystem writers. No Windows,
multiprocess, directory-fsync or power-loss durability guarantee is claimed.
