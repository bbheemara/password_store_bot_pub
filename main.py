import discord
from discord.ext import commands
from discord import app_commands
import logging
from dotenv import load_dotenv
import os
from io import BytesIO

from discord.ui import Modal, TextInput, View, Button

from utils.encryptor import encrypt_password, decrypt_password
from utils.storage import (
    store_password, get_password, delete_password, get_all_services,
    get_master_pass, set_master_pass, verify_master_pass
)

load_dotenv()
token = os.getenv('DISCORD_TOKEN')

handler = logging.FileHandler('discord.log', encoding='utf-8', mode='w')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash commands")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")

@bot.event
async def on_member_join(member):
    await member.send("Welcome to the server! 😉")

class MasterPasswordModal(Modal, title="🔐 Set Master Password"):
    password = TextInput(label="Master Password", placeholder="Enter a strong password", style=discord.TextStyle.short, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        set_master_pass(interaction.user.id, self.password.value)
        await interaction.response.send_message("✅ Master password set! You can now store and retrieve passwords.", ephemeral=True)



class VerifyMasterPasswordModal(Modal, title="🔑 Enter Master Password"):
    def __init__(self, action, service=None):
        super().__init__()
        self.action = action
        self.service = service
        self.password = TextInput(label="Master Password", placeholder="Enter your master password", style=discord.TextStyle.short, required=True)
        self.add_item(self.password)

    async def on_submit(self, interaction: discord.Interaction):
        if verify_master_pass(interaction.user.id, self.password.value):
            if self.action == "get":
                encrypted = get_password(interaction.user.id, self.service)
                if not encrypted:
                    await interaction.response.send_message(f"❌ No password found for `{self.service}`.", ephemeral=True)
                else:
                    decrypted = decrypt_password(encrypted)
                    await interaction.response.send_message(f"🔑 Your password for `{self.service}` is: `{decrypted}`", ephemeral=True,delete_after=35)
            elif self.action == "update":
                await interaction.response.send_modal(UpdatePasswordModal(self.service))
            elif self.action == "delete":
                if delete_password(interaction.user.id, self.service):
                    await interaction.response.send_message(f"✅ Deleted password for `{self.service}`.", ephemeral=True,delete_after=35)
                else:
                    await interaction.response.send_message(f"❌ No password to delete for `{self.service}`.", ephemeral=True,delete_after=35)
            elif self.action == "export":
                full = get_password(interaction.user.id, full_dump=True)
                if not full:
                    await interaction.response.send_message("No passwords to export!", ephemeral=True)
                else:
                    lines = [f"{svc}: {decrypt_password(enc)}" for svc, enc in full.items()]
                    buf = BytesIO("\n".join(lines).encode())
                    file = discord.File(buf, filename="vault_export.txt")
                    await interaction.response.send_message("Here is your vault export:", file=file, ephemeral=True,delete_after=35)
        else:
            await interaction.response.send_message("❌ Incorrect master password.", ephemeral=True)




class StorePasswordModal(Modal, title="🔐 Store a Password"):
    service = TextInput(label="Service Name", placeholder="e.g. GitHub")
    password = TextInput(label="Password", placeholder="Enter password", style=discord.TextStyle.short)

    async def on_submit(self, interaction: discord.Interaction):
        encrypted = encrypt_password(self.password.value)
        store_password(interaction.user.id, self.service.value, encrypted)
        await interaction.response.send_message(
            f"✅ Stored password for `{self.service.value}`!", ephemeral=True,delete_after=35
        )




class StorePasswordView(View):
    @discord.ui.button(label="Store New Password", style=discord.ButtonStyle.primary)
    async def button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(StorePasswordModal())




class UpdatePasswordModal(Modal):
    def __init__(self, service: str):
        super().__init__(title="🔁 Update Your Password")
        self.service_name = service
        self.password_field = TextInput(
            label="New Password",
            placeholder="Enter new password",
            style=discord.TextStyle.short,
            required=True
        )
        self.add_item(self.password_field)



    async def on_submit(self, interaction: discord.Interaction):
        encrypted = encrypt_password(self.password_field.value)
        store_password(interaction.user.id, self.service_name, encrypted)
        await interaction.response.send_message(
            f"✅ Password updated for `{self.service_name}`!", ephemeral=True,delete_after=35
        )



@bot.tree.command(name="start", description="Initialize and set master password or store new password")
async def start_slash(interaction: discord.Interaction):
    if not get_master_pass(interaction.user.id):
        await interaction.response.send_modal(MasterPasswordModal())
    else:
        await interaction.response.send_message(
            f"👋 Hi {interaction.user.name}! Click below to store a new password securely:",
            view=StorePasswordView(),
            ephemeral=True
        )




@bot.tree.command(name="get", description="Retrieve a password (requires master password)")
async def get_slash(interaction: discord.Interaction, service: str):
    if not get_master_pass(interaction.user.id):
        await interaction.response.send_message("🔐 Please set a master password first using `/start`.", ephemeral=True)
        return
    await interaction.response.send_modal(VerifyMasterPasswordModal("get", service))




@bot.tree.command(name="update", description="Update a password (requires master password)")
async def update_slash(interaction: discord.Interaction, service: str):
    if not get_master_pass(interaction.user.id):
        await interaction.response.send_message("🔐 Please set a master password first using `/start`.", ephemeral=True)
        return
    await interaction.response.send_modal(VerifyMasterPasswordModal("update", service))




@bot.tree.command(name="delete", description="Delete a password (requires master password)")
async def delete_slash(interaction: discord.Interaction, service: str):
    if not get_master_pass(interaction.user.id):
        await interaction.response.send_message("🔐 Please set a master password first using `/start`.", ephemeral=True)
        return
    await interaction.response.send_modal(VerifyMasterPasswordModal("delete", service))




@bot.tree.command(name="export", description="Export all passwords (requires master password)")
async def export_slash(interaction: discord.Interaction):
    if not get_master_pass(interaction.user.id):
        await interaction.response.send_message("🔐 Please set a master password first using `/start`.", ephemeral=True)
        return
    await interaction.response.send_modal(VerifyMasterPasswordModal("export"))



@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if 'shit' in message.content.lower():
        await message.delete()
        await message.channel.send(
            f"{message.author.mention}, please watch your language!", delete_after=5
        )
    await bot.process_commands(message)




@bot.command()
async def list(ctx):
    if not isinstance(ctx.channel, discord.DMChannel):
        return await ctx.send("❌ Please use this command in a DM.", delete_after=8)
    services = get_all_services(ctx.author.id)
    if not services:
        return await ctx.send("You have no saved passwords.", delete_after=8)
    await ctx.send(f"🔐 You've saved passwords for: `{', '.join(services)}`", delete_after=20)




@bot.command()
async def helpme(ctx):
    await ctx.send(
        "**🔐 Password Store Bot**\n\n"
        "**Slash Commands (Recommended):**\n"
        "`/start` – Set master password or store new password\n"
        "`/get <service>` – Retrieve password (requires master password)\n"
        "`/update <service>` – Update password (requires master password)\n"
        "`/delete <service>` – Delete password (requires master password)\n"
        "`/export` – Export vault (requires master password)\n\n"
        "**Classic Commands:**\n"
        "`!list` – List services\n"
        "`!helpme` – This menu\n"
        "`!about` – About the bot",
        delete_after=60
    )




@bot.command()
async def about(ctx):
    await ctx.send(
        "**About**\n"
        "A secure, encrypted password manager inside Discord.\n"
        "Uses bcrypt for master password hashing and Fernet for service password encryption.\n"
        "All sensitive operations happen via slash commands with modals!",
        delete_after=60
    )

    

bot.run(token, log_handler=handler, log_level=logging.DEBUG)