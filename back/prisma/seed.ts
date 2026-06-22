/* eslint-disable no-console */
import { createHash, randomBytes } from 'crypto';

import { PrismaClient, Role } from '@prisma/client';
import * as bcrypt from 'bcrypt';

const prisma = new PrismaClient();

const INITIAL_CREDITS = 30;

async function main(): Promise<void> {
  const skipSeed =
    process.env.PRISMA_SKIP_SEED === 'true' || process.env.SKIP_SEED === 'true';
  if (skipSeed) {
    console.log('PRISMA_SKIP_SEED is set - skipping seeding');
    return;
  }

  const users = [
    {
      firstName: 'admin',
      lastName: 'template',
      email: 'admin@template.com',
      password: 'Admin@123',
      role: Role.ADMIN,
    },
    {
      firstName: 'user',
      lastName: 'template',
      email: 'user@template.com',
      password: 'User@123',
      role: Role.USER,
    },
  ];

  for (const u of users) {
    const passwordHash = await bcrypt.hash(u.password, 10);

    const user = await prisma.user.upsert({
      where: { email: u.email },
      update: {},
      create: {
        firstName: u.firstName,
        lastName: u.lastName,
        email: u.email,
        password: passwordHash,
        role: u.role,
      },
    });

    await prisma.creditAccount.upsert({
      where: { userId: user.id },
      update: {},
      create: { userId: user.id, balance: INITIAL_CREDITS },
    });

    console.log(`Seeded user ${u.email} (${u.role})`);
  }

  // ---- Agentic Dev Maestro: empresa demo + agente + projeto ----
  const owner = await prisma.user.findUnique({
    where: { email: 'admin@template.com' }
  });
  if (owner) {
    const company = await prisma.company.upsert({
      where: { slug: 'demo' },
      update: {},
      create: { name: 'Empresa Demo', slug: 'demo' }
    });

    const membership = await prisma.membership.upsert({
      where: { userId_companyId: { userId: owner.id, companyId: company.id } },
      update: {},
      create: { userId: owner.id, companyId: company.id, role: 'OWNER' }
    });

    let project = await prisma.project.findUnique({
      where: { companyId_key: { companyId: company.id, key: 'DEMO' } }
    });
    if (!project) {
      project = await prisma.project.create({
        data: {
          companyId: company.id,
          name: 'Projeto Demo',
          key: 'DEMO',
          boards: {
            create: {
              name: 'Principal',
              columns: {
                create: [
                  { name: 'Backlog', order: 0 },
                  { name: 'A fazer', order: 1 },
                  { name: 'Fazendo', order: 2 },
                  { name: 'Revisão', order: 3 },
                  { name: 'Concluído', order: 4, isDone: true }
                ]
              }
            }
          }
        }
      });
    }

    // Recria a chave 'seed-agent' para que o segredo fique disponível no log.
    await prisma.apiKey.deleteMany({
      where: { companyId: company.id, label: 'seed-agent' }
    });
    const secret = `adm_${randomBytes(24).toString('hex')}`;
    await prisma.apiKey.create({
      data: {
        label: 'seed-agent',
        hashedKey: createHash('sha256').update(secret).digest('hex'),
        prefix: secret.slice(0, 12),
        scopes: [
          'projects:read',
          'projects:write',
          'tasks:read',
          'tasks:write',
          'tasks:move'
        ],
        companyId: company.id,
        membershipId: membership.id
      }
    });

    console.log('\n=== Agentic Dev Maestro (seed) ===');
    console.log(`Empresa : ${company.name} (id=${company.id}, slug=${company.slug})`);
    console.log(`Projeto : ${project.name} (id=${project.id}, key=${project.key})`);
    console.log('API key do agente (header x-api-key):');
    console.log(`  ${secret}`);
    console.log('==================================\n');
  }
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
