const fs = require('node:fs');
const { initializeTestEnvironment, assertSucceeds, assertFails } = require('@firebase/rules-unit-testing');
const firebase = require('firebase/compat/app');
require('firebase/compat/firestore');

async function main() {
  const env = await initializeTestEnvironment({
    projectId: 'demo-senlis',
    firestore: { rules: fs.readFileSync('firestore.rules', 'utf8') },
  });
  try {
    const alice = env.authenticatedContext('alice').firestore();
    const bob = env.authenticatedContext('bob').firestore();
    const anon = env.unauthenticatedContext().firestore();
    const stamp = () => firebase.firestore.FieldValue.serverTimestamp();
    const product = '32dfdfd355015cdb894eee0d264f687b';
    const message = alice.collection('rooms').doc('global').collection('messages').doc('real');
    await assertSucceeds(alice.collection('users').doc('alice').set({
      display_name: 'Alice', created_at: stamp(),
    }));
    await assertFails(bob.collection('users').doc('alice').set({
      display_name: 'Bob', created_at: stamp(),
    }));
    await assertSucceeds(message.set({
      uid: 'alice', author: 'Alice', body: 'Gerçek deneyim', status: 'visible', created_at: stamp(),
    }));
    await assertFails(bob.collection('rooms').doc('global').collection('messages').doc('fake').set({
      uid: 'alice', author: 'Alice', body: 'Sahte', status: 'visible', created_at: stamp(),
    }));
    await assertSucceeds(anon.collection('rooms').doc('global').collection('messages')
      .where('status', '==', 'visible').orderBy('created_at', 'desc').limit(50).get());
    await assertFails(anon.collection('rooms').doc('global').collection('messages').limit(50).get());
    await assertSucceeds(alice.collection('ratings').doc(product).collection('users').doc('alice')
      .set({ uid: 'alice', stars: 4, updated_at: stamp() }));
    await assertFails(bob.collection('ratings').doc(product).collection('users').doc('alice')
      .set({ uid: 'alice', stars: 5, updated_at: stamp() }));
    await assertFails(alice.collection('news').doc('fabricated').set({
      title: 'Sahte haber', reviewed: true,
    }));
    await env.withSecurityRulesDisabled(async context => {
      await context.firestore().collection('rooms').doc('global').collection('messages').doc('hidden')
        .set({ uid: 'alice', body: 'gizli', status: 'hidden', created_at: new Date() });
    });
    await assertFails(anon.collection('rooms').doc('global').collection('messages').doc('hidden').get());
    console.log('Firestore rules: ownership, visible queries, ratings and editorial news verified');
  } finally {
    await env.cleanup();
  }
}

main().catch(error => { console.error(error); process.exitCode = 1; });
