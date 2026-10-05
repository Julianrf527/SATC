import { memo } from "react";

function ImgProfile() {
  const randomNum = Math.floor(Math.random() * 10) + 1;
  const iconProfile = `/assets/iconsProfile/${randomNum}.jpg`;

  return <img src={iconProfile} alt={`Foto Perfil ${randomNum}`} />;
}

export default memo(ImgProfile);
